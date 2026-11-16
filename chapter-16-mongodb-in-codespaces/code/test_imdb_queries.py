import unittest

import imdb_queries as q


class BuildFilterTests(unittest.TestCase):
    def test_empty_form_gives_empty_filter(self):
        self.assertEqual(q.build_filter(), {})
        self.assertEqual(q.build_filter("  ", "", 0), {})

    def test_fields_are_trimmed_and_year_is_a_number(self):
        self.assertEqual(
            q.build_filter(" The Godfather ", "movie", "1972"),
            {"primary_title": "The Godfather", "title_type": "movie", "start_year": 1972},
        )


class ExplainSummaryTests(unittest.TestCase):
    def report(self, plan, keys, docs, returned, millis):
        return {
            "queryPlanner": {"winningPlan": plan},
            "executionStats": {
                "totalKeysExamined": keys,
                "totalDocsExamined": docs,
                "nReturned": returned,
                "executionTimeMillis": millis,
            },
        }

    def test_collection_scan(self):
        plan = {"stage": "LIMIT", "inputStage": {"stage": "COLLSCAN"}}
        out = q.explain_summary(self.report(plan, 0, 900, 20, 41))
        self.assertEqual(out["plan"], "LIMIT > COLLSCAN")
        self.assertEqual((out["docs_examined"], out["returned"], out["millis"]), (900, 20, 41))

    def test_index_scan_and_slot_based_wrapper(self):
        plan = {"queryPlan": {"stage": "FETCH", "inputStage": {"stage": "IXSCAN"}}}
        out = q.explain_summary(self.report(plan, 47, 47, 47, 0))
        self.assertEqual(out["plan"], "FETCH > IXSCAN")
        self.assertEqual(out["keys_examined"], 47)


if __name__ == "__main__":
    unittest.main()
