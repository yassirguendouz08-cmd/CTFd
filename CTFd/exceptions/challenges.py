class ChallengeCreateException(Exception):
    def __init__(self, message="Challenge creation failed", status_code=500):
        super().__init__(message)
        self.status_code = status_code


class ChallengeUpdateException(Exception):
    def __init__(self, message="Challenge update failed", status_code=500):
        super().__init__(message)
        self.status_code = status_code


class ChallengeSolveException(Exception):
    pass
