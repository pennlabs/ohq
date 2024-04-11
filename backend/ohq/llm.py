from django.conf import settings
import openai
import pinecone


def generateResponse(question, llmSettings):

    openai.api_key = settings.OPENAI_API_KEY
    pinecone.init(api_key=settings.PINECONE_API_KEY, environment=settings.PINECONE_ENV_KEY)

    llm_prompt = llmSettings.llm_prompt
    if llmSettings.input_prompt:
        llm_prompt += "\n" + "Here are some additional instructions provided by the course professor/head TA" + " \n" + llmSettings.input_prompt
    response = openai.ChatCompletion.create(
        messages = [{
            "role": "user", 
            "content":
            f"""
            What are the topics asked about in this question: {question}
            OUTPUT ONLY KEYWORDS
            Below are examples, where the question is deliminated in ticks, your response is in brackets, and each example is separated by commas:
            'How to do question 4?': question 4,
            'I'm confused on how Dijkstra's works': Dijkstra's
            """
            }],
        temperature = float(llmSettings.temperature),
        model= "gpt-4-1106-preview"
    )

    query = response["choices"][0]["message"]["content"]
    index = pinecone.Index("ohq-test")

    embedding = openai.Embedding.create(input=[query], engine="text-embedding-ada-002")
    query_vector = embedding["data"][0]["embedding"]

    items = index.query(query_vector, top_k=2, include_metadata=True)
    contexts = [x["metadata"]["text"] for x in items["matches"]]

    if len(contexts)>0:
        st = f"""
Here are two pieces course materials, separated by a line of "#", to guide your answer:
{contexts[0]}
############
{contexts[1]}
        """
        llm_prompt = llm_prompt.replace("\\CONTEXT\\", st)

    
    messages = [
        {"role": "system", "content": llm_prompt},
        {"role": "user", "content": question}
    ]

    response = openai.ChatCompletion.create(
        messages = messages,
        temperature = float(llmSettings.temperature),
        model= "gpt-4-1106-preview"
    )
    content = response["choices"][0]["message"]["content"]
    prompt_tokens = response["usage"]["prompt_tokens"]
    completion_tokens = response["usage"]["completion_tokens"]
    total_tokens = prompt_tokens + completion_tokens
    # print(content)
    return content