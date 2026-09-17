#!/usr/bin/env python3
"""Browser checks for the static homepage. Requires playwright and local Chrome."""
import functools
import http.server
import threading
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright
from serve_site import SiteHandler

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SiteHandler):
    def log_message(self, *args):
        pass


class HomepageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(ROOT)))
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}/"
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(executable_path="/usr/bin/google-chrome",
                                            args=["--no-sandbox"])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.page = self.browser.new_page(viewport={"width": 1440, "height": 1000})
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.goto(self.url)

    def tearDown(self):
        self.page.close()

    def test_results_use_actual_addressing_conditions_without_converting_missing_to_zero(self):
        self.assertTrue(self.page.locator("#results-body").count(), "Homepage results are missing")
        row = self.page.locator('#results-body tr[data-model="minicpm"]')
        self.assertIn("95.00", row.inner_text())
        self.assertIn("47.30", row.inner_text())
        self.page.get_by_role("button", name="Implicit", exact=True).click()
        self.assertIn("94.35", row.inner_text())
        self.assertIn("46.65", row.inner_text())
        self.assertNotRegex(self.page.locator('body').inner_text(), r'\b(?:SRC|FLIP)\b')
        self.assertIn("n/a", self.page.locator('#results-body tr[data-model="freezeomni"]').inner_text())

    def test_model_switch_keeps_scenario_and_resets_playback(self):
        self.assertTrue(self.page.locator("#demo-audio").count(), "Audio demo is missing")
        self.page.wait_for_function("document.querySelector('#demo-audio').readyState >= 1")
        scenario = self.page.locator("#scenario-label").inner_text()
        self.page.locator("#demo-audio").evaluate("a => { a.currentTime = 2; }")
        self.page.select_option("#model-select", index=1)
        self.assertEqual(scenario, self.page.locator("#scenario-label").inner_text())
        self.assertTrue(self.page.locator("#demo-audio").evaluate("a => a.paused && a.currentTime === 0"))
        self.assertNotIn("moshi", self.page.locator("#demo-audio").get_attribute("src"))
        self.assertTrue(self.page.locator('[data-marker="resolver"]').count())

    def test_all_examples_load_and_seek_controls_work(self):
        self.assertTrue(self.page.locator("#demo-audio").count(), "Audio demo is missing")
        for category in ["respond", "accuracy", "silence", "yield"]:
            self.page.locator(f'[data-example="{category}"]').click()
            self.assertEqual(self.page.locator("#model-select option").count(), 4)
            for index in range(4):
                self.page.select_option("#model-select", index=index)
                self.page.wait_for_function("document.querySelector('#demo-audio').readyState >= 1")
                self.assertGreater(self.page.locator("#demo-audio").evaluate("a => a.duration"), 3)
        self.page.locator('[data-seek="resolver"]').click()
        position = self.page.locator("#demo-audio").evaluate("a => a.currentTime")
        self.assertAlmostEqual(position, 6.132, delta=.05)
        self.assertEqual(self.errors, [])

    def test_mobile_layout_and_local_assets(self):
        self.assertTrue(self.page.locator("main").count(), "Homepage is missing")
        self.page.set_viewport_size({"width": 390, "height": 844})
        self.assertTrue(self.page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
        paths = self.page.locator("[src], a[href]").evaluate_all(
            "els => els.map(e => e.getAttribute('src') || e.getAttribute('href')).filter(p => p && !/^(#|https?:|mailto:)/.test(p))")
        for path in paths:
            self.assertEqual(self.page.request.get(self.url + path).status, 200, path)
        self.assertEqual(self.errors, [])

    def test_playback_advances_and_clipboard_copies_the_citation(self):
        self.page.context.grant_permissions(["clipboard-read", "clipboard-write"])
        self.page.wait_for_function("document.querySelector('#demo-audio').readyState >= 1")
        self.page.locator("#demo-audio").evaluate("a => a.play()")
        self.page.wait_for_function("document.querySelector('#demo-audio').currentTime > .2")
        self.page.select_option("#model-select", index=1)
        self.assertTrue(self.page.locator("#demo-audio").evaluate("a => a.paused"))
        self.page.get_by_role("button", name="Copy citation").click()
        self.page.wait_for_function("document.querySelector('#copy-status').textContent === 'Copied'")
        self.assertEqual(self.page.evaluate("navigator.clipboard.readText()"),
                         self.page.locator("#bibtex").inner_text())

    def test_missing_audio_offers_a_download_and_recovers_on_switch(self):
        source = self.page.locator("#demo-audio").get_attribute("src")
        self.page.route("**/" + source, lambda route: route.abort())
        self.page.reload()
        self.page.wait_for_function("!document.querySelector('#audio-error').hidden")
        self.assertTrue(self.page.locator("#audio-download").is_visible())
        self.page.select_option("#model-select", index=1)
        self.page.wait_for_function("document.querySelector('#demo-audio').readyState >= 1")
        self.assertTrue(self.page.locator("#audio-error").is_hidden())

    def test_only_passing_examples_expose_names_and_removed_audio_is_unavailable(self):
        for category in ["respond", "accuracy", "silence", "yield"]:
            self.page.locator(f'[data-example="{category}"]').click()
            for index in range(4):
                self.page.select_option("#model-select", index=index)
                label = self.page.locator("#model-select option:checked").inner_text()
                verdict_class = self.page.locator("#verdict").get_attribute("class")
                if "fail" in verdict_class or "neutral" in verdict_class:
                    self.assertRegex(label, r"^Anonymous model [A-Z]$")
                else:
                    self.assertIn(label, ["MiniCPM-o 4.5", "Moshi", "FLM-Audio", "Freeze-Omni"])
                self.assertNotIn("Voila", self.page.locator("#examples").inner_text())
                self.assertRegex(self.page.locator("#demo-audio").get_attribute("src"),
                                 r"^assets/audio/[a-z]+-[a-f0-9]{16}\.mp3$")
        for model in ["minicpm", "moshi", "flm", "voila"]:
            for category in ["respond", "accuracy", "silence", "yield"]:
                self.assertEqual(self.page.request.get(self.url + f"assets/audio/{category}-{model}.mp3").status, 404)
        # Demo selection must not remove models from the full results table.
        self.assertEqual(self.page.locator("#results-body tr").count(), 5)
        self.assertIn("Voila", self.page.locator("#results-body").inner_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
