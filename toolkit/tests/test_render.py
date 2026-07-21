import unittest

from ci_rescue.models import Analysis, Finding
from ci_rescue.render import render_markdown


class MarkdownRenderTests(unittest.TestCase):
    def test_workflow_data_cannot_create_links_images_or_html(self):
        marker = "https://malicious.invalid/collect"
        analysis = Analysis(
            "workflow",
            "[open me]({0})".format(marker),
            [
                Finding(
                    "WF999",
                    "warning",
                    "Synthetic finding",
                    "Click [this link]({0})".format(marker),
                    "Load ![tracking image]({0})".format(marker),
                    ["<img src='{0}'>".format(marker)],
                )
            ],
            {},
        )

        report = render_markdown(analysis)

        self.assertIn("- Input: `[open me]({0})`".format(marker), report)
        self.assertNotIn("Click [this link]", report)
        self.assertNotIn("![", report)
        self.assertIn(r"\<img", report)
        self.assertIn(r"https\:\/\/malicious\.invalid\/collect", report)

    def test_privacy_footer_describes_report_metadata(self):
        report = render_markdown(Analysis("workflow", "workflow.yml", [], {}))

        self.assertIn("workflow identifiers", report)
        self.assertIn("Raw logs and full input files are not included", report)


if __name__ == "__main__":
    unittest.main()
