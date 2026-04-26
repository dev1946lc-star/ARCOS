import asyncio
import logging

logger = logging.getLogger("JobMarket")

class JobMarket:
    def __init__(self):
        self.pending_jobs = []
        self.completed_jobs = []

    def add_job(self, job):
        self.pending_jobs.append(job)
        logger.info(f"Market received new job: {job['task_id']} | Price: {job['price_offer']} WEI")

    def get_available_job(self):
        if self.pending_jobs:
            return self.pending_jobs.pop(0)
        return None

    def get_best_job(self, scorer, limit=5):
        if not self.pending_jobs:
            return None
        search_limit = max(1, min(int(limit), len(self.pending_jobs)))
        window = self.pending_jobs[:search_limit]
        best_index = max(range(len(window)), key=lambda idx: scorer(window[idx]))
        return self.pending_jobs.pop(best_index)

    def complete_job(self, job, result):
        job['result'] = result
        self.completed_jobs.append(job)
        logger.info(f"Market marked job {job['task_id']} as completed.")
