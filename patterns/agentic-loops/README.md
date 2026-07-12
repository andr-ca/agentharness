# Agentic Loop Patterns

Structured patterns for building multi-turn agent interactions, tool calling loops, and agentic workflows.

An **agentic loop** is a cycle where an agent:
1. Receives a task or state
2. Plans / reasons about next steps
3. Calls tools or takes actions
4. Observes outcomes
5. Repeats until done

This pattern appears in LLM-powered systems, AI orchestrators, and automated workflows.

---

## Basic Loop Structure

### Minimal Loop

```python
def agentic_loop(task: str, max_iterations: int = 10):
    """Minimal agent loop: think → act → observe → repeat."""
    state = {"task": task, "iteration": 0}
    
    while state["iteration"] < max_iterations:
        # 1. Think: decide next action
        action = agent.plan(state)
        
        # 2. Act: execute action
        result = execute_action(action)
        
        # 3. Observe: update state
        state["iteration"] += 1
        state["last_result"] = result
        
        # 4. Check: are we done?
        if is_complete(state):
            return state["last_result"]
    
    raise TimeoutError("Agent did not complete within max iterations")
```

### Production Loop

```python
import inspect
import json
from typing import Any, Callable, Dict, List
from dataclasses import dataclass, field

def _validate_arguments(fn: Callable, arguments: Dict[str, Any]) -> None:
    """Fail before calling `fn` if a required parameter is missing."""
    sig = inspect.signature(fn)
    missing = [
        name for name, param in sig.parameters.items()
        if param.default is inspect.Parameter.empty and name not in arguments
    ]
    if missing:
        raise ValueError(f"Missing required arguments: {missing}")

@dataclass
class AgentState:
    task: str
    messages: List[Dict[str, Any]] = field(default_factory=list)  # Conversation history
    current_action: str = None
    iteration: int = 0
    max_iterations: int = 10
    tools_called: List[str] = None
    
    def __post_init__(self):
        if self.tools_called is None:
            self.tools_called = []

class Agent:
    def __init__(self, model, tools: Dict[str, Callable], logger):
        self.model = model
        self.tools = tools
        self.logger = logger
    
    def run(self, task: str) -> Dict[str, Any]:
        """Run agent loop with error handling and observability."""
        # Seed the conversation with the task — without this the model
        # is called with an empty history and never sees what it's for.
        state = AgentState(task=task, messages=[{"role": "user", "content": task}])
        
        try:
            while state.iteration < state.max_iterations:
                state.iteration += 1
                
                # 1. Think: LLM generates next action
                self.logger.info(f"Iteration {state.iteration}", 
                               extra={"task": task})
                
                response = self.model.complete(
                    messages=state.messages,
                    tools=list(self.tools.keys()),
                )
                
                # 2. Parse: extract action from response
                state.messages.append({
                    "role": "assistant",
                    "content": response["content"]
                })
                
                action = response.get("tool_call")
                if not action:
                    # Agent decided it's done
                    return {
                        "status": "complete",
                        "result": response["content"],
                        "iterations": state.iteration,
                    }
                
                state.current_action = action["name"]
                # The model's response identifies which call this is
                # (OpenAI: tool_calls[i].id, Anthropic: content block id).
                # Without threading it through, a provider that supports
                # concurrent/parallel tool calls in one turn can't tell
                # which result answers which call.
                call_id = action.get("id")
                
                # 3. Act: call tool
                try:
                    tool_fn = self.tools.get(action["name"])
                    if not tool_fn:
                        raise ValueError(f"Unknown tool: {action['name']}")
                    
                    # Reject missing required arguments against the
                    # tool's own signature before calling it, rather
                    # than letting a malformed call surface as a bare
                    # TypeError from Python's own argument binding.
                    arguments = action.get("arguments", {})
                    _validate_arguments(tool_fn, arguments)
                    
                    tool_result = tool_fn(**arguments)
                    state.tools_called.append(action["name"])
                    
                except Exception as e:
                    self.logger.error("Tool error", extra={
                        "tool": action["name"],
                        "call_id": call_id,
                        "error": str(e),
                        "iteration": state.iteration,
                    })
                    tool_result = f"Error: {str(e)}"
                
                # 4. Observe: add result to conversation. Use a "tool"
                # role with the call id, not a plain "user" message — the
                # exact shape is provider-specific (OpenAI wants
                # {"role": "tool", "tool_call_id": ..., "content": ...};
                # Anthropic wants a "tool_result" content block on a user
                # message), so translate this generic form at the
                # self.model boundary rather than hard-coding one API.
                state.messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": action["name"],
                    "content": tool_result if isinstance(tool_result, str) else json.dumps(tool_result),
                })
                
                self.logger.info("Tool executed", extra={
                    "tool": action["name"],
                    "call_id": call_id,
                    "iteration": state.iteration,
                })
        
        except Exception as e:
            self.logger.error("Agent loop failed", extra={
                "task": task,
                "iteration": state.iteration,
                "error": str(e),
            })
            return {
                "status": "error",
                "error": str(e),
                "iterations": state.iteration,
            }
        
        # Max iterations reached without completion
        return {
            "status": "max_iterations_reached",
            "last_action": state.current_action,
            "iterations": state.iteration,
            "tools_called": state.tools_called,
        }
```

---

## Tool Calling

### Tool Definition

```python
from typing import Callable, Dict, Any
import inspect

class Tool:
    def __init__(self, name: str, fn: Callable, description: str):
        self.name = name
        self.fn = fn
        self.description = description
        self.schema = self._extract_schema(fn)
    
    def _extract_schema(self, fn: Callable) -> Dict[str, Any]:
        """Extract parameter schema from function signature."""
        sig = inspect.signature(fn)
        params = {}
        
        for param_name, param in sig.parameters.items():
            # Use type hints and docstring to build schema
            params[param_name] = {
                "type": param.annotation.__name__,
                "description": f"Parameter: {param_name}",
            }
        
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": params,
                    "required": list(params.keys()),
                }
            }
        }
    
    def call(self, **kwargs) -> str:
        """Call tool and return result."""
        try:
            result = self.fn(**kwargs)
            return json.dumps(result) if not isinstance(result, str) else result
        except TypeError as e:
            return f"Invalid arguments: {str(e)}"

# Define tools
def search_web(query: str) -> Dict[str, Any]:
    """Search the web for information."""
    # Implementation
    return {"results": [...]}

def read_file(path: str) -> str:
    """Read a file and return its contents."""
    with open(path) as f:
        return f.read()

def write_file(path: str, content: str) -> Dict[str, str]:
    """Write content to a file."""
    with open(path, 'w') as f:
        f.write(content)
    return {"status": "written", "path": path}

# Registry
tools = {
    "search_web": Tool("search_web", search_web, "Search the web"),
    "read_file": Tool("read_file", read_file, "Read a file"),
    "write_file": Tool("write_file", write_file, "Write to a file"),
}
```

---

## Patterns & Best Practices

### Pattern: Reflection & Course Correction

Agent observes its own actions and corrects course if needed:

```python
def run_with_reflection(agent, task: str, max_iterations: int = 5, max_attempts: int = 15):
    """Run agent with per-iteration reflection."""
    state = {"task": task, "reflections": [], "iteration": 0}
    attempts = 0
    
    # Loop on `attempts`, not `iteration` — iteration only advances on
    # progress, so gating the loop on it alone never stops a reflection
    # that keeps reporting is_progress=False.
    while state["iteration"] < max_iterations and attempts < max_attempts:
        attempts += 1
        
        # Execute action
        action = agent.plan(state)
        result = execute(action)
        
        # Reflect on result
        reflection = agent.reflect(state, action, result)
        state["reflections"].append(reflection)
        
        if reflection["is_progress"]:
            state["iteration"] += 1
        else:
            # Try different approach
            state["message"] = f"Reflection: {reflection['advice']}"
    
    return state
```

### Pattern: Tool Chaining

One tool's output becomes the input to the next:

```python
def chain_tools(tools: List[str], initial_input: Any) -> Any:
    """Chain tools: output of one → input of next."""
    result = initial_input
    
    for tool_name in tools:
        tool = get_tool(tool_name)
        result = tool(result)
        logger.info(f"Chained {tool_name}", extra={"result": result})
    
    return result

# Usage
chain_tools(
    ["fetch_data", "transform_data", "save_data"],
    initial_input="/path/to/input"
)
```

### Pattern: Conditional Branching

Agent decides path based on outcomes:

```python
def run_with_branching(agent, task: str):
    """Agent branches logic based on intermediate results."""
    state = {"task": task, "branch": None}
    
    # First step: classify task
    classification = agent.classify(task)
    state["branch"] = classification  # "simple", "complex", "data_heavy"
    
    if state["branch"] == "simple":
        # Direct solution
        return agent.solve_simple(task)
    elif state["branch"] == "complex":
        # Multi-step reasoning
        return agent.solve_complex(task)
    elif state["branch"] == "data_heavy":
        # Fetch data first
        data = agent.fetch_data(task)
        return agent.solve_with_data(task, data)
```

### Pattern: Consensus / Voting

Multiple agents vote on next action. This is majority voting, not
independent validation — if the agents share a model, prompt, or
training data bias, they tend to make the *same* mistake together, and
a unanimous wrong vote looks identical to a unanimous right one. Don't
present this as a correctness guarantee; it catches independent,
uncorrelated errors, not systematic ones.

```python
def multi_agent_consensus(agents: List[Agent], task: str):
    """Multiple agents propose actions; choose by vote."""
    proposals = []
    
    for agent in agents:
        action = agent.propose_action(task)
        proposals.append(action)
    
    # Vote on best proposal
    votes = {}
    for proposal in proposals:
        key = proposal["action"]
        votes[key] = votes.get(key, 0) + 1
    
    best_action = max(votes, key=votes.get)
    logger.info("Consensus reached", extra={
        "action": best_action,
        "votes": votes,
    })
    
    return execute(best_action)
```

---

## Common Pitfalls

| Pitfall | Problem | Fix |
|---------|---------|-----|
| Infinite loops | Agent stuck in repeat cycle | Add iteration limit + timeout |
| Token explosion | LLM runs out of context (long message history) | Summarize old messages, use sliding window |
| Tool errors ignored | Agent continues on tool failure | Catch and feed error back to agent |
| No observability | Can't debug what agent is doing | Log every action, tool call, and decision |
| Hard-coded actions | Agent can't adapt | Parameterize tools and strategies |

---

## Observability & Debugging

```python
class LoggingAgent(Agent):
    def run(self, task: str) -> Dict[str, Any]:
        """Run with comprehensive logging."""
        trace_id = generate_id()
        
        self.logger.info("Agent started", extra={
            "trace_id": trace_id,
            "task": task,
        })
        
        result = super().run(task)
        
        self.logger.info("Agent finished", extra={
            "trace_id": trace_id,
            "status": result["status"],
            "iterations": result.get("iterations"),
            "tools_called": result.get("tools_called"),
        })
        
        return result
```

---

## Further Reading

- OpenAI Responses API: Tool use and function calling (the Assistants
  API is deprecated, with a sunset scheduled for August 26, 2026 — see
  OpenAI's [migration guide](https://developers.openai.com/api/docs/guides/migrate-to-responses))
- LangChain: Agent orchestration frameworks
- ReAct: Reasoning and Acting in Language Models (Yao et al.)
- Anthropic Agents: Building agentic systems with Claude
