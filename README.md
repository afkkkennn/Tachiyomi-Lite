# Tachiyomi Lite (experimental)

A small, unofficial performance overlay for [Mihon](https://github.com/mihonapp/mihon), targeting lower-memory Android phones such as the Samsung Galaxy A16 5G with 4 GB RAM.

## Included in v0.1

- **Auto Lite Mode** on devices reporting < 5 GiB of physical RAM. Overrides are available in Reader Settings → Lite.
- **Bounded network prefetch:** read the visible page first, preload fewer surrounding pages and use smaller download chunks when Lite Mode is on.
- **Smaller Webtoon view cache** and cached-view trimming after Android low-memory signals.
- **WebView return recovery:** retry nearby failed chapter pages after the built-in chapter WebView is closed. This **does not bypass Cloudflare/CAPTCHA**.
- Custom **Tachiyomi Lite** launcher label. Debug application ID remains `app.mihon.dev` — check for conflicts if you already have Mihon debug installed.

The source code and settings UI are overlaid onto a pinned upstream Mihon revision during an automated build. The original Mihon repository is not copied into this repository.

## Get an APK

1. Open the [Actions tab](../../actions/workflows/build-tachiyomi-lite.yml).
2. Select **Build Tachiyomi Lite APK** → **Run workflow**, or examine the latest automatic push build.
3. After a **successful** workflow run, open **Artifacts** and download the debug APK ZIP.
4. Extract it and install the appropriate APK on your phone (arm64-v8a if an ABI-specific build is produced).

**Do not install an APK from a failed build.** Android may warn about sideloading. Back up your Mihon library before migration. Debug builds aren't production releases and aren't automatically updated.

## Run locally

Requirements: Python 3, Git, JDK 21, Android SDK.

```sh
git clone https://github.com/mihonapp/mihon.git mihon
python3 -m unittest discover -s tests -v
python3 apply_lite.py mihon --check
python3 apply_lite.py mihon
cd mihon
./gradlew :app:assembleStandardDebug --no-daemon
```

For a reproducible build, check out the upstream SHA pinned in `.github/workflows/build-tachiyomi-lite.yml` before patching.

## Status and limitations

This is experimental source code, **not a verified fast APK**. Local smoke tests validate changes to text anchors, not Kotlin compilation, function correctness, or on-device performance. GitHub Actions provides the first Android compile check. No device benchmarking has been performed yet. Long webtoon chapters, real sources, and login/session behavior must be tested on the Samsung Galaxy A16.

Source licensing: Mihon is Apache-2.0 licensed. This overlay is also Apache-2.0, without official endorsement or affiliation.
