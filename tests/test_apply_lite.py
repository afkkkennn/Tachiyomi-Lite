"""Smoke-test the fail-closed Mihon source overlay without requiring the Android SDK."""
import unittest
from pathlib import Path
from apply_lite import patch_files, READER, DIALOG

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
        android:label="@string/app_name"
""",
        }

    def test_patch(self):
        out = patch_files(self.fixtures())
        self.assertEqual(len(out), 7)
        self.assertIn("liteMode() -> (index - 1)..(index + 2)", out[READER / "loader/HttpPageLoader.kt"])
        self.assertIn("ReaderLitePolicy.enabled(context)", out[READER / "loader/ChapterLoader.kt"])
        self.assertIn("trimPageCache()", out[READER / "ReaderActivity.kt"])
        self.assertIn("onRetryFailedPages = ::retryNearbyFailedPages", out[READER / "ReaderActivity.kt"])
        self.assertIn("Retry nearby failed pages", out[DIALOG])
        self.assertIn("3 -> LiteSettingsPage()", out[DIALOG])

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
