This is a very common point of frustration when moving from standard playground chat boxes (like ChatGPT or Claude) to custom code nodes in LangGraph. You use the exact same prompt and the exact same model, but the API node spits out a dry, 3-sentence summary while the web chat gives you a beautifully formatted, deep, detailed answer.

There are three technical reasons this happens, and they are all easily fixable.

---

## 1. System Prompt & "Chat Wrapper" Contamination

When you type a prompt into a consumer web chat interface, the studio wraps your prompt in a massive, hidden **System Prompt** designed to make the AI sound like a helpful, detailed assistant. It inserts instructions like: *"Be detailed, use markdown formatting, explain your reasoning step-by-step, and provide thorough answers."*

When you invoke a raw LLM inside a LangGraph node, **you lose that wrapper entirely.** The model defaults to its bare-minimum behavior, which is to be as concise as possible to save tokens.

### How to fix it:

You must explicitly build that premium chat experience into your node's system prompt or prompt template:

* **Enforce depth:** Add a structural mandate: *"Provide an exhaustive, multi-paragraph analysis. Do not summarize unless explicitly requested."*
* **Ask for structural thinking:** Include instructions for structure: *"Break your answer down using markdown headers (`##`), bullet points, and bold text for readability."*

---

## 2. The `max_tokens` Default Trap

Many development SDKs automatically set a conservative default limit on output tokens (often **256** or **512 tokens**) when you instantiate a model wrapper (`ChatOpenAI`, `ChatAnthropic`, etc.) unless you explicitly override it.

Because the model knows its output length is capped, it truncates its thoughts and generates a much shorter response so it doesn't get awkwardly sliced off mid-sentence.

### How to fix it:

When declaring the model for your LangGraph node, intentionally increase or open up the maximum generation limit:

```python
# Force the model to allow long-form generation
model = ChatAnthropic(model="claude-3-5-sonnet", max_tokens=4000)

```

---

## 3. The Lack of Chat History Context

In a standard web chat page, the entire past conversation is continuously packed together and fed back into the model, giving it a massive cushion of context to build detailed thoughts upon.

In LangGraph, if your node functions are isolating data or overwriting variables instead of accumulating a clean message thread, the model views your prompt as a completely isolated "one-shot" question, leading to a much shorter answer.

### How to fix it:

Ensure your LangGraph state uses the built-in `MessagesState` or uses an append operator (`operator.add`) for messages. When passing the prompt to the model inside the node, make sure you feed it the *entire* accumulated history, not just the single latest prompt string.

---

## 4. Temperature Adjustments

Web chat applications often set their internal `temperature` slightly higher (around **0.7** to **0.9**) to encourage creative, expressive, and detailed prose. API wrappers frequently default to a colder setting (like **0.0** or **0.2**) to ensure strict, analytical consistency. Colder temperatures inherently generate more clinical, brief, and direct responses.

### How to fix it:

If your node is handling creative tasks like script writing, character creation, or brainstorming, bump the temperature up inside the node's model definition:

```python
model = ChatOpenAI(model="gpt-4o", temperature=0.8, max_tokens=2048)

```
