class Memory:
    def __init__(self):
        self.short_term = []
        self.preferences = {} # 'item_name': float score

    def add(self, text):
        self.short_term.append(text)
        if len(self.short_term) > 10:
            self.short_term.pop(0)

    def learn(self, subject, score):
        curr = self.preferences.get(subject, 0.0)
        self.preferences[subject] = curr + 0.1 * (score - curr)

    def get_context(self):
        return "\n".join(self.short_term[-3:])
