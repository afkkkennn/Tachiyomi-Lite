"""Smoke-test the fail-closed Mihon source overlay without requiring the Android SDK."""
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from xml.etree import ElementTree
from apply_lite import apply, patch_files, READER, DIALOG

ANDROID = "{http://schemas.android.com/apk/res/android}"
READER_ACTIVITY = READER / "ReaderActivity.kt"
PHASE3_FIXTURE = f"""diff --git a/{READER_ACTIVITY} b/{READER_ACTIVITY}
--- a/{READER_ACTIVITY}
+++ b/{READER_ACTIVITY}
@@ -5,3 +5,3 @@
                         onHideMenus = {{ setMenuVisibility(false) }},
-                        onRetryFailedPages = ::retryNearbyFailedPages,
+                        onRetryFailedPages = ::retryAfterVerification,
                         viewModel = settingsViewModel,
"""

class OverlayTest(unittest.TestCase):
    def fixtures(self):
        return {
            READER / "loader/HttpPageLoader.kt": """
    private val canLoadAhead: () -> Boolean,
) : PageLoader() {
        pages.loadByRollingChunked(page.index, 3, 5) { chunks ->
        val window = if (canLoadAhead()) items.indices else (index - 1)..(index + LIMITED_PAGES_AHEAD)
""",
            READER / "loader/ChapterLoader.kt": """
import eu.kanade.tachiyomi.ui.reader.model.ReaderChapter
            source is HttpSource -> HttpPageLoader(chapter, source, chapterCache, appScope, canLoadAhead)
""",
            READER / "viewer/webtoon/WebtoonViewer.kt": """
import eu.kanade.tachiyomi.ui.reader.ReaderActivity
        recycler.setItemViewCacheSize(RECYCLER_VIEW_CACHE_SIZE)
    /**
     * Destroys this viewer. Called when leaving the reader or swapping viewers.
     */
""",
            READER / "ReaderActivity.kt": """
import eu.kanade.tachiyomi.source.online.HttpSource
import eu.kanade.tachiyomi.ui.reader.viewer.Viewer
    private var assistUrl: String? = null
                        onHideMenus = { setMenuVisibility(false) },
                        viewModel = settingsViewModel,
    override fun onResume() {
        super.onResume()
        viewModel.restartReadTimer()
    override fun onPause() {
        viewModel.saveHistory()
        super.onPause()
    }
            startActivity(intent)
        }
    }

    private fun openChapterInBrowser() {
""",
            DIALOG: """
import androidx.compose.foundation.layout.Column
    onHideMenus: () -> Unit,
    viewModel: ReaderSettingsViewModel,
        stringResource(MR.strings.custom_filter),
    )
                    2 -> ColorFilterPage(viewModel)
""",
            Path("app/src/main/AndroidManifest.xml"): """
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:roundIcon="@mipmap/ic_launcher" />
</manifest>
""",
            Path("app/src/main/res/mipmap/ic_launcher.xml"): """
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@drawable/ic_launcher_background"/>
    <foreground android:drawable="@drawable/ic_launcher_foreground"/>
    <monochrome android:drawable="@drawable/ic_launcher_monochrome"/>
</adaptive-icon>
""",
            Path("app/src/main/res/values/themes.xml"): """
<resources>
    <style name="Theme.Tachiyomi.SplashScreen" parent="Theme.SplashScreen">
        <item name="windowSplashScreenAnimatedIcon">@drawable/ic_mihon_splash</item>
        <item name="windowSplashScreenBackground">@color/splash</item>
    </style>
</resources>
""",
        }

    def test_patch(self):
        out = patch_files(self.fixtures())
        self.assertEqual(len(out), 9)
        self.assertIn("liteMode() -> (index - 1)..(index + 2)", out[READER / "loader/HttpPageLoader.kt"])
        self.assertIn("ReaderLitePolicy.enabled(context)", out[READER / "loader/ChapterLoader.kt"])
        self.assertIn("trimPageCache()", out[READER / "ReaderActivity.kt"])
        self.assertIn("onRetryFailedPages = ::retryNearbyFailedPages", out[READER / "ReaderActivity.kt"])
        self.assertIn("Retry nearby failed pages", out[DIALOG])
        self.assertIn("3 -> LiteSettingsPage(onRetryFailedPages)", out[DIALOG])

    def test_applied_branding_resolves_launcher_and_splash_resources(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_fixtures(root)
            phase3 = root / "fixture.patch"
            phase3.write_text(PHASE3_FIXTURE, encoding="utf-8")
            with patch("apply_lite.PHASE3_PATCH", phase3):
                apply(root, check=True)
                self.assertNotIn("onRetryFailedPages", (root / READER_ACTIVITY).read_text(encoding="utf-8"))
                apply(root)
            self.assertIn("::retryAfterVerification", (root / READER_ACTIVITY).read_text(encoding="utf-8"))

            app = root / "app/src/main"
            resources = app / "res"
            manifest = ElementTree.parse(app / "AndroidManifest.xml")
            application = manifest.find("application")
            self.assertEqual(application.attrib[f"{ANDROID}label"], "@string/kisap_name")
            brand = ElementTree.parse(resources / "values/kisap_brand.xml")
            self.assertEqual(brand.findtext("string[@name='kisap_name']"), "Kisap")

            icon = application.attrib[f"{ANDROID}icon"]
            self.assertEqual(application.attrib[f"{ANDROID}roundIcon"], icon)
            launcher = ElementTree.parse(resources / f"{icon.removeprefix('@')}.xml")
            background = launcher.find("background").attrib[f"{ANDROID}drawable"]
            background_name = background.removeprefix("@color/")
            self.assertIsNotNone(brand.findtext(f"color[@name='{background_name}']"))
            for layer in ("foreground", "monochrome"):
                drawable = launcher.find(layer).attrib[f"{ANDROID}drawable"]
                vector = ElementTree.parse(resources / f"{drawable.removeprefix('@')}.xml")
                self.assertEqual(vector.getroot().tag, "vector")

            themes = ElementTree.parse(resources / "values/themes.xml")
            splash = themes.find("style[@name='Theme.Tachiyomi.SplashScreen']")
            self.assertEqual(splash.findtext("item[@name='windowSplashScreenBackground']"), background)
            self.assertEqual(
                splash.findtext("item[@name='windowSplashScreenAnimatedIcon']"),
                launcher.find("foreground").attrib[f"{ANDROID}drawable"],
            )

    def test_phase_three_context_mismatch_does_not_write_base_overlay(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_fixtures(root)
            phase3 = root / "fixture.patch"
            phase3.write_text(
                PHASE3_FIXTURE.replace("::retryNearbyFailedPages", "::unknownRetry"),
                encoding="utf-8",
            )
            with patch("apply_lite.PHASE3_PATCH", phase3):
                with self.assertRaises(subprocess.CalledProcessError):
                    apply(root)
            for path, content in self.fixtures().items():
                self.assertEqual((root / path).read_text(encoding="utf-8"), content)
            self.assertFalse((root / READER / "ReaderLitePolicy.kt").exists())

    def write_fixtures(self, root):
        for path, content in self.fixtures().items():
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

    def test_changed_upstream_fails(self):
        files = self.fixtures()
        path = READER / "loader/HttpPageLoader.kt"
        files[path] = files[path].replace("page.index, 3, 5", "page.index, 1, 3")
        with self.assertRaisesRegex(ValueError, "HTTP rolling chunk"):
            patch_files(files)

    def test_double_patch_fails(self):
        with self.assertRaises(ValueError):
            patch_files(patch_files(self.fixtures()))

if __name__ == "__main__":
    unittest.main()
