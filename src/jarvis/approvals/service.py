class ApprovalService:
    def __init__(self, repository, policy_engine):
        self.repository = repository
        self.policy_engine = policy_engine

    def request(self, *, task_id, action, risk, payload):
        return self.repository.request(task_id, action, str(risk), payload)
