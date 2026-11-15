export type Week = {
  n: number;
  title: string;
  source: string;
  goal: string;
  project: string;
  url: string;
};

// From the "Become an AI Engineer" 12-week plan (python basics assumed, 10-15 h/week).
export const WEEKS: Week[] = [
  { n: 1, title: 'Python Foundations', source: 'Harvard CS50P', goal: 'Write, test and debug Python.', project: 'A small CLI tool that reads a file and prints a summary.', url: 'https://cs50.harvard.edu/python/' },
  { n: 2, title: 'Practical Deep Learning', source: 'fast.ai', goal: 'Train useful models quickly.', project: 'Train an image classifier on your own photos.', url: 'https://course.fast.ai/' },
  { n: 3, title: 'Neural Nets from Scratch', source: 'Andrej Karpathy', goal: 'Understand backprop by building it, toward a tiny GPT.', project: 'Re-implement micrograd and a character-level model.', url: 'https://karpathy.ai/zero-to-hero.html' },
  { n: 4, title: 'PyTorch Fundamentals', source: 'PyTorch', goal: 'Tensors, gradients and training loops.', project: 'Train a small network end to end in PyTorch.', url: 'https://pytorch.org/tutorials/' },
  { n: 5, title: 'LLMs & Fine-Tuning', source: 'Hugging Face', goal: 'Tokens, transformers, attention and adaptation.', project: 'Fine-tune a small model on a narrow task.', url: 'https://huggingface.co/learn/llm-course' },
  { n: 6, title: 'Build LLM Applications', source: 'Full Stack Deep Learning', goal: 'Connect a model to a product: prompt, LLM, app, evaluate, iterate.', project: 'Ship a tiny LLM web app with a basic eval.', url: 'https://fullstackdeeplearning.com/llm-bootcamp/' },
  { n: 7, title: 'Retrieval-Augmented AI', source: 'DataTalks.Club', goal: 'Ground answers in your own documents.', project: 'Q&A bot over your own notes, with citations.', url: 'https://github.com/DataTalksClub/llm-zoomcamp' },
  { n: 8, title: 'Build AI Agents', source: 'Hugging Face', goal: 'Reason, act, observe loops.', project: 'An agent that uses 2-3 tools to finish a task.', url: 'https://huggingface.co/learn/agents-course' },
  { n: 9, title: 'Agent Architecture', source: 'Anthropic', goal: 'Compose reliable workflows: route, parallelize, evaluate.', project: 'Turn week 8 into a routed, evaluated workflow.', url: 'https://www.anthropic.com/engineering/building-effective-agents' },
  { n: 10, title: 'Connect Tools with MCP', source: 'Hugging Face', goal: 'Give systems useful tools through MCP.', project: 'Build and connect your own MCP server.', url: 'https://huggingface.co/learn/mcp-course' },
  { n: 11, title: 'Production Engineering', source: 'Made With ML', goal: 'Test, serve and monitor.', project: 'Add tests, logging and latency tracking to your app.', url: 'https://madewithml.com/' },
  { n: 12, title: 'Ship & Maintain Models', source: 'MLOps Zoomcamp', goal: 'Track, deploy, improve, repeat.', project: 'Deploy something real and monitor it for a week.', url: 'https://github.com/DataTalksClub/mlops-zoomcamp' },
];

export const STEPS = ['Core material', 'Exercises', 'Mini project'] as const;

export const CONCEPTS: { term: string; def: string }[] = [
  { term: 'Agent', def: 'An AI system that can reason, plan and act autonomously.' },
  { term: 'Planner', def: 'Breaks high-level goals into sub-tasks.' },
  { term: 'Tool-using agent', def: 'An agent that uses APIs or plugins to complete tasks.' },
  { term: 'RAG', def: 'Retrieval-Augmented Generation: answers using a knowledge base.' },
  { term: 'Memory', def: 'Stores past interactions for continuity (short-term scratchpad, long-term store).' },
  { term: 'Reflex agent', def: 'Reacts to current input without memory.' },
  { term: 'Deliberative agent', def: 'Plans actions based on a goal and a model of the world.' },
  { term: 'Multi-agent system', def: 'Multiple agents working together on a task, with defined roles.' },
  { term: 'Feedback loop', def: 'Uses evaluation to improve performance over time.' },
  { term: 'AgentOps', def: 'Practices and tooling to monitor, scale and manage agents.' },
  { term: 'Orchestration', def: 'Frameworks and workflow engines that coordinate steps (LangChain, CrewAI, AutoGen).' },
  { term: 'Reflection / retry', def: 'The execution loop: act, check the result, self-correct.' },
];
