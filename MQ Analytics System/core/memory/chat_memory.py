class ChatMemory:
    def __init__(self):
        self.history = []

    def add(self, query, response):
        self.history.append({
            "query": query,
            "response": response
        })

    def get_context(self):
        context = ""
        for h in self.history[-5:]:   # last 5 messages
            context += f"User: {h['query']}\nAssistant: {h['response']}\n\n"
        return context

