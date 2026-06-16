from concurrent.futures import ThreadPoolExecutor, as_completed
import time


class ParallelExecutor:
    def __init__(self, tool_registry, max_workers=3):
        self.tools = tool_registry
        self.max_workers = max_workers

    def execute_plan(self, plan, on_step=None):
        results = {}
        completed = set()

        def run_step(step):
            if on_step:
                on_step(step)
            try:
                result = self.tools.execute(step["tool"], **step["args"])
                return step["step"], True, result
            except Exception as e:
                return step["step"], False, str(e)

        while len(completed) < len(plan):
            ready = [
                s for s in plan
                if s["step"] not in completed
                and all(dep in completed for dep in s.get("depends_on", []))
            ]
            if not ready:
                break

            with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
                futures = {pool.submit(run_step, s): s for s in ready}
                for future in as_completed(futures):
                    step_num, success, result = future.result()
                    results[step_num] = {"success": success, "result": result}
                    completed.add(step_num)

            if on_step:
                on_step(None)

        return results

    def execute_tool(self, tool_name, **kwargs):
        return self.tools.execute(tool_name, **kwargs)

    def execute_parallel(self, tasks):
        results = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {}
            for task_id, tool_name, kwargs in tasks:
                future = pool.submit(self.tools.execute, tool_name, **kwargs)
                futures[future] = task_id
            for future in as_completed(futures):
                task_id = futures[future]
                try:
                    results[task_id] = {"success": True, "result": future.result()}
                except Exception as e:
                    results[task_id] = {"success": False, "result": str(e)}
        return results
