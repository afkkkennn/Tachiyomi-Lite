#!/usr/bin/env python3
"""Fail-closed Mihon source overlay for the experimental Kisap reader."""
from pathlib import Path
import argparse

READER = Path("app/src/main/java/eu/kanade/tachiyomi/ui/reader")
DIALOG = Path("app/src/main/java/eu/kanade/presentation/reader/settings/ReaderSettingsDialog.kt")
MANIFEST = Path("app/src/main/AndroidManifest.xml")
APP_RES = Path("app/src/main/res")
LAUNCHER_ICON = APP_RES / "mipmap/ic_launcher.xml"
THEMES = APP_RES / "values/themes.xml"
BRAND_RESOURCES = (
    Path("drawable/kisap_foreground.xml"),
    Path("drawable/kisap_monochrome.xml"),
    Path("values/kisap_brand.xml"),
)

POLICY = """package eu.kanade.tachiyomi.ui.reader

import android.app.ActivityManager
import android.content.Context

/** A small on-device reader policy. AUTO targets devices with less than 5 GiB physical RAM. */
internal object ReaderLitePolicy {
    const val AUTO = 0
    const val ON = 1
    const val OFF = 2

    private const val STORE = "reader_lite_settings"
    private const val MODE_KEY = "mode"
    private const val AUTO_LIMIT_BYTES = 5L * 1024 * 1024 * 1024

    fun mode(context: Context): Int = context.applicationContext
        .getSharedPreferences(STORE, Context.MODE_PRIVATE)
        .getInt(MODE_KEY, AUTO)

    fun setMode(context: Context, value: Int) {
        require(value in AUTO..OFF)
        context.applicationContext.getSharedPreferences(STORE, Context.MODE_PRIVATE)
            .edit().putInt(MODE_KEY, value).apply()
    }

    fun enabled(context: Context): Boolean = when (mode(context)) {
        ON -> true
        OFF -> false
        else -> automaticallyEnabled(context)
    }

    private fun automaticallyEnabled(context: Context): Boolean {
        val manager = context.getSystemService(Context.ACTIVITY_SERVICE) as? ActivityManager
            ?: return false
        if (manager.isLowRamDevice) return true
        val info = ActivityManager.MemoryInfo()
        manager.getMemoryInfo(info)
        return info.totalMem in 1L until AUTO_LIMIT_BYTES
    }
}
"""

LITE_UI = """

/** Reader memory-mode controls. Reopen the chapter after changing modes. */
@Composable
private fun LiteSettingsPage(onRetryFailedPages: () -> Unit) {
    val context = LocalContext.current
    var mode by remember { mutableIntStateOf(ReaderLitePolicy.mode(context)) }
    Column(modifier = Modifier.padding(16.dp)) {
        Text("Lite reader mode", style = MaterialTheme.typography.titleMedium)
        Text("Limits prefetch and recycled views to reduce memory use on 4 GB phones.")
        listOf(
            ReaderLitePolicy.AUTO to "Automatic (recommended)",
            ReaderLitePolicy.ON to "Always on",
            ReaderLitePolicy.OFF to "Off",
        ).forEach { (value, description) ->
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable {
                        ReaderLitePolicy.setMode(context, value)
                        mode = value
                    },
            ) {
                RadioButton(
                    selected = mode == value,
                    onClick = {
                        ReaderLitePolicy.setMode(context, value)
                        mode = value
                    },
                )
                Text(description)
            }
        }
        Button(onClick = onRetryFailedPages) {
            Text("Retry nearby failed pages")
        }
        Text(
            "Open a new chapter to apply changes. CAPTCHA challenges may still need manual verification.",
            style = MaterialTheme.typography.bodySmall,
        )
    }
}
"""

def replace_once(content: str, old: str, new: str, label: str) -> str:
    count = content.count(old)
    if count != 1:
        raise ValueError(f"{label}: expected exactly one source anchor, found {count}")
    return content.replace(old, new, 1)

def patch_files(originals: dict[Path, str]) -> dict[Path, str]:
    """Transform all files in memory first; abort without partial writes on anchor mismatch."""
    files = dict(originals)

    http = READER / "loader/HttpPageLoader.kt"
    s = files[http]
    s = replace_once(s, "    private val canLoadAhead: () -> Boolean,\n) : PageLoader() {",
        "    private val canLoadAhead: () -> Boolean,\n    private val liteMode: () -> Boolean,\n) : PageLoader() {",
        "HTTP loader constructor")
    s = replace_once(s, "        pages.loadByRollingChunked(page.index, 3, 5) { chunks ->",
        "        pages.loadByRollingChunked(\n            page.index,\n            if (liteMode()) 1 else 3,\n            if (liteMode()) 2 else 5,\n        ) { chunks ->",
        "HTTP rolling chunk")
    s = replace_once(s,
        "        val window = if (canLoadAhead()) items.indices else (index - 1)..(index + LIMITED_PAGES_AHEAD)",
        "        val window = when {\n            liteMode() -> (index - 1)..(index + 2)\n            canLoadAhead() -> items.indices\n            else -> (index - 1)..(index + LIMITED_PAGES_AHEAD)\n        }",
        "HTTP prefetch window")
    files[http] = s

    chapter = READER / "loader/ChapterLoader.kt"
    s = files[chapter]
    s = replace_once(s, "import eu.kanade.tachiyomi.ui.reader.model.ReaderChapter",
        "import eu.kanade.tachiyomi.ui.reader.ReaderLitePolicy\nimport eu.kanade.tachiyomi.ui.reader.model.ReaderChapter",
        "ChapterLoader policy import")
    s = replace_once(s,
        "            source is HttpSource -> HttpPageLoader(chapter, source, chapterCache, appScope, canLoadAhead)",
        "            source is HttpSource -> HttpPageLoader(\n                chapter, source, chapterCache, appScope, canLoadAhead,\n                liteMode = { ReaderLitePolicy.enabled(context) },\n            )",
        "ChapterLoader HTTP call")
    files[chapter] = s

    webtoon = READER / "viewer/webtoon/WebtoonViewer.kt"
    s = files[webtoon]
    s = replace_once(s, "import eu.kanade.tachiyomi.ui.reader.ReaderActivity",
        "import eu.kanade.tachiyomi.ui.reader.ReaderActivity\nimport eu.kanade.tachiyomi.ui.reader.ReaderLitePolicy",
        "Webtoon policy import")
    s = replace_once(s, "        recycler.setItemViewCacheSize(RECYCLER_VIEW_CACHE_SIZE)",
        "        recycler.setItemViewCacheSize(if (ReaderLitePolicy.enabled(activity)) 1 else RECYCLER_VIEW_CACHE_SIZE)",
        "Webtoon cache size")
    s = replace_once(s,
        "    /**\n     * Destroys this viewer. Called when leaving the reader or swapping viewers.\n     */",
        "    /** Release recycled views on Android memory-pressure notifications. */\n    fun trimPageCache() {\n        recycler.setItemViewCacheSize(0)\n        recycler.recycledViewPool.clear()\n    }\n\n    /**\n     * Destroys this viewer. Called when leaving the reader or swapping viewers.\n     */",
        "Webtoon trim hook")
    files[webtoon] = s

    reader = READER / "ReaderActivity.kt"
    s = files[reader]
    s = replace_once(s, "import eu.kanade.tachiyomi.source.online.HttpSource",
        "import eu.kanade.tachiyomi.source.model.Page\nimport eu.kanade.tachiyomi.source.online.HttpSource",
        "Reader Page import")
    s = replace_once(s, "import eu.kanade.tachiyomi.ui.reader.viewer.Viewer\n",
        "import eu.kanade.tachiyomi.ui.reader.viewer.Viewer\nimport eu.kanade.tachiyomi.ui.reader.viewer.webtoon.WebtoonViewer\n",
        "Reader Webtoon import")
    s = replace_once(s, "    private var assistUrl: String? = null",
        "    private var assistUrl: String? = null\n    private var retryFailedPagesAfterWebView = false",
        "Reader recovery flag")
    s = replace_once(s, "    override fun onResume() {\n        super.onResume()\n        viewModel.restartReadTimer()",
        """    override fun onResume() {
        super.onResume()
        if (retryFailedPagesAfterWebView) {
            retryFailedPagesAfterWebView = false
            // Browser verification can refresh source cookies. Retry only failed nearby pages.
            val state = viewModel.state.value
            val chapter = state.currentChapter
            val index = (state.currentPage - 1).coerceAtLeast(0)
            chapter?.pages.orEmpty()
                .filter { it.index in (index - 1)..(index + 2) && it.status is Page.State.Error }
                .forEach { page -> chapter?.pageLoader?.retryPage(page) }
        }
        viewModel.restartReadTimer()""",
        "Reader onResume")
    s = replace_once(s,
        "    override fun onPause() {\n        viewModel.saveHistory()\n        super.onPause()\n    }",
        """    override fun onPause() {
        viewModel.saveHistory()
        super.onPause()
    }

    override fun onTrimMemory(level: Int) {
        super.onTrimMemory(level)
        if (level >= android.content.ComponentCallbacks2.TRIM_MEMORY_RUNNING_LOW &&
            ReaderLitePolicy.enabled(this)
        ) {
            (viewer as? WebtoonViewer)?.trimPageCache()
        }
    }""",
        "Reader memory callback")
    s = replace_once(s,
        "            startActivity(intent)\n        }\n    }\n\n    private fun openChapterInBrowser() {",
        "            retryFailedPagesAfterWebView = true\n            startActivity(intent)\n        }\n    }\n\n    private fun openChapterInBrowser() {",
        "Reader WebView flag")
    s = replace_once(s,
        "                        onHideMenus = { setMenuVisibility(false) },\n                        viewModel = settingsViewModel,",
        "                        onHideMenus = { setMenuVisibility(false) },\n                        onRetryFailedPages = ::retryNearbyFailedPages,\n                        viewModel = settingsViewModel,",
        "Reader settings retry callback")
    s = replace_once(s,
        "    override fun onPause() {\n        viewModel.saveHistory()\n        super.onPause()\n    }",
        """    private fun retryNearbyFailedPages() {
        val state = viewModel.state.value
        val chapter = state.currentChapter ?: return
        val index = (state.currentPage - 1).coerceAtLeast(0)
        chapter.pages.orEmpty()
            .filter { it.index in (index - 1)..(index + 3) && it.status is Page.State.Error }
            .forEach { page -> chapter.pageLoader?.retryPage(page) }
    }

    override fun onPause() {
        viewModel.saveHistory()
        super.onPause()
    }""",
        "Reader manual retry")
    files[reader] = s

    dialog = files[DIALOG]
    dialog = replace_once(dialog,
        "    onHideMenus: () -> Unit,\n    viewModel: ReaderSettingsViewModel,",
        "    onHideMenus: () -> Unit,\n    onRetryFailedPages: () -> Unit,\n    viewModel: ReaderSettingsViewModel,",
        "Reader dialog retry parameter")
    dialog = replace_once(dialog, "import androidx.compose.foundation.layout.Column",
        """import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.clickable
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Text
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import eu.kanade.tachiyomi.ui.reader.ReaderLitePolicy""",
        "Reader dialog imports")
    dialog = replace_once(dialog,
        "        stringResource(MR.strings.custom_filter),\n    )",
        '        stringResource(MR.strings.custom_filter),\n        "Lite",\n    )',
        "Reader settings Lite tab")
    dialog = replace_once(dialog, "                    2 -> ColorFilterPage(viewModel)",
        "                    2 -> ColorFilterPage(viewModel)\n                    3 -> LiteSettingsPage(onRetryFailedPages)",
        "Reader settings page")
    files[DIALOG] = dialog + LITE_UI
    files[READER / "ReaderLitePolicy.kt"] = POLICY

    files[MANIFEST] = replace_once(files[MANIFEST],
        '        android:label="@string/app_name"',
        '        android:label="@string/kisap_name"',
        "Launcher label")
    files[LAUNCHER_ICON] = replace_once(files[LAUNCHER_ICON],
        """    <background android:drawable="@drawable/ic_launcher_background"/>
    <foreground android:drawable="@drawable/ic_launcher_foreground"/>
    <monochrome android:drawable="@drawable/ic_launcher_monochrome"/>""",
        """    <background android:drawable="@color/kisap_background"/>
    <foreground android:drawable="@drawable/kisap_foreground"/>
    <monochrome android:drawable="@drawable/kisap_monochrome"/>""",
        "Adaptive launcher layers")
    files[THEMES] = replace_once(files[THEMES],
        """        <item name="windowSplashScreenAnimatedIcon">@drawable/ic_mihon_splash</item>
        <item name="windowSplashScreenBackground">@color/splash</item>""",
        """        <item name="windowSplashScreenAnimatedIcon">@drawable/kisap_foreground</item>
        <item name="windowSplashScreenBackground">@color/kisap_background</item>""",
        "Splash screen branding")
    return files

def apply(root: Path, check: bool = False) -> None:
    affected = (
        READER / "loader/HttpPageLoader.kt",
        READER / "loader/ChapterLoader.kt",
        READER / "viewer/webtoon/WebtoonViewer.kt",
        READER / "ReaderActivity.kt",
        DIALOG,
        MANIFEST,
        LAUNCHER_ICON,
        THEMES,
    )
    originals = {p: (root / p).read_text(encoding="utf-8") for p in affected}
    generated = patch_files(originals)
    branding = Path(__file__).resolve().parent / "branding"
    for resource in BRAND_RESOURCES:
        generated[APP_RES / resource] = (branding / resource).read_text(encoding="utf-8")
    if check:
        print(f"PASS: {len(affected)} Mihon files and {len(BRAND_RESOURCES)} branding resources ready for overlay")
        return
    for path, content in generated.items():
        dest = root / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        print("Updated", path)
    print("Kisap experimental overlay applied.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    apply(args.root.resolve(), args.check)
