## How does an agent call work?

1. User asks a question
2. We decide if the question can be answered by just SQLCoder, or whether it needs an agent to answer the call. This is done using the `get_classification` function, which then makes a call to `https://api.defog.ai/classify_question`

- if the classification is SQLCoder only, we just use SQLCoder to answer the question and return the answer
- if the classification is "Agents", we move on to Step 3

3. We use a class called the "Clarifier" to see if the question asked was clear enough, or if it needs further refinements
4. If we have these clarifications, we can convert the question + the clarification statement into a "clearer" question, using another LLM call
5. We then give the clarified question to a "Planner" agent

- The planner agent then comes up with the first step of a plan, and determines if additional steps are needed to answer the question
- It executes this first step, along with retries in case of errors
- It then gets the data returned from the first step, and stores it
- It keeps producing additional steps until no additional steps are needed

6. [optional] If making a REST call, it can return the final answer to the user at this point

# Rest APIs

- Clarifier API (easy => make a request to the api.defog.ai server)
- Summarizer API (easy => make a request to the api.defog.ai server)
- PlannerAndExecutorAPI
  - plan out an agent and execute it
