package com.example.barrysconcertagenda

import android.content.ContentValues
import android.graphics.Bitmap
import android.os.Environment
import android.provider.MediaStore
import androidx.activity.ComponentActivity
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsSelected
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onAllNodesWithTag
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.getUnclippedBoundsInRoot
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTouchInput
import androidx.compose.ui.test.swipeLeft
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import java.time.LocalDate
import java.time.YearMonth
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.Rule
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class BackstageCalendarUiTest {
    @get:Rule val compose = createComposeRule()

    @Test fun tappingNovember22AndAgainTogglesTheSelection() {
        val day = LocalDate.of(2026, 11, 22)
        var selected by mutableStateOf<LocalDate?>(null)
        compose.setContent {
            MaterialTheme {
                BackstageCalendar(
                    month = YearMonth.of(2026, 11),
                    eventDays = setOf(day),
                    selectedDay = selected,
                    onPrevious = {},
                    onNext = {},
                    onSelectDay = { selected = it }
                )
            }
        }
        compose.onNodeWithText("November 2026").assertIsDisplayed()
        compose.onNodeWithText("22").performClick()
        compose.runOnIdle { assertEquals(day, selected) }
        compose.onNodeWithText("22").performClick()
        compose.runOnIdle { assertEquals(null, selected) }
    }

    @Test fun calendarMonthArrowsInvokeTheirActions() {
        var previous = 0
        var next = 0
        compose.setContent {
            MaterialTheme {
                BackstageCalendar(
                    month = YearMonth.of(2026, 11),
                    eventDays = emptySet(),
                    selectedDay = null,
                    onPrevious = { previous++ },
                    onNext = { next++ },
                    onSelectDay = {}
                )
            }
        }
        compose.onNodeWithText("‹").performClick()
        compose.onNodeWithText("›").performClick()
        compose.runOnIdle {
            assertEquals(1, previous)
            assertEquals(1, next)
        }
    }
}

@RunWith(AndroidJUnit4::class)
class BackstageNavigationUiTest {
    @get:Rule val compose = createAndroidComposeRule<MainActivity>()

    private fun captureAppScreen(name: String) {
        // Export a REAL Compose screenshot via MediaStore. Gradle uninstalls
        // instrumentation apps after tests: app-private external files may
        // disappear before adb can pull them. Public Pictures persists.
        compose.waitForIdle()
        val app = InstrumentationRegistry.getInstrumentation().targetContext
        val resolver = app.contentResolver
        val values = ContentValues().apply {
            put(MediaStore.Images.Media.DISPLAY_NAME, "$name.png")
            put(MediaStore.Images.Media.MIME_TYPE, "image/png")
            put(MediaStore.Images.Media.RELATIVE_PATH,
                Environment.DIRECTORY_PICTURES + "/BarryConcertAgendaV3Test")
            put(MediaStore.Images.Media.IS_PENDING, 1)
        }
        val uri = resolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values)
            ?: error("Unable to create public screenshot: $name")
        resolver.openOutputStream(uri)?.use { stream ->
            compose.onRoot().captureToImage().asAndroidBitmap()
                .compress(Bitmap.CompressFormat.PNG, 100, stream)
        } ?: error("Unable to write public screenshot: $name")
        values.clear()
        values.put(MediaStore.Images.Media.IS_PENDING, 0)
        resolver.update(uri, values, null, null)
    }

    @Test fun welcomeScreenOpensFiveMainIconsAndMore() {
        compose.onNodeWithContentDescription("Barry's concert agenda").performClick()
        compose.waitUntil(timeoutMillis = 60_000) {
            compose.onAllNodesWithText("Home").fetchSemanticsNodes().isNotEmpty() &&
                compose.onAllNodesWithText("Concerten controleren...")
                    .fetchSemanticsNodes().isEmpty()
        }
        captureAppScreen("home")
        for (item in listOf("Home", "Ontdek", "Agenda", "Mijn tickets", "Favorieten", "Meer")) {
            compose.onNodeWithContentDescription(item).assertIsDisplayed()
        }
        compose.onNodeWithContentDescription("Mijn tickets").performClick()
        captureAppScreen("tickets")
        compose.onNodeWithContentDescription("Favorieten").performClick()
        compose.onNodeWithContentDescription("Favorieten").assertIsSelected()
        captureAppScreen("favorites")
        compose.onNodeWithContentDescription("Agenda").performClick()
        compose.onNodeWithContentDescription("Agenda").assertIsSelected()
        captureAppScreen("agenda")
    }

    @Test fun swipingHomeMovesToDiscoverTab() {
        compose.onNodeWithContentDescription("Barry's concert agenda").performClick()
        compose.onNodeWithContentDescription("Home").assertIsSelected()
        compose.onRoot().performTouchInput { swipeLeft() }
        compose.onNodeWithContentDescription("Ontdek").assertIsSelected()
    }

    @Test fun originalPhotoAppearsOnlyOnInfoPageAndFillsScreen() {
        compose.onNodeWithContentDescription("Barry's concert agenda").performClick()
        // Home and Discover are intentionally plain, not photo-backed.
        compose.onNodeWithTag("backstage-fullscreen-start-photo").assertDoesNotExist()
        compose.onNodeWithContentDescription("Ontdek").performClick()
        compose.onNodeWithTag("backstage-fullscreen-start-photo").assertDoesNotExist()
        captureAppScreen("discover")
        // In V3 the photo is shown only underneath Info, edge-to-edge,
        // with lavender text directly over the picture (without a card).
        compose.onNodeWithContentDescription("Meer").performClick()
        // The remote feed is still loading on a fresh emulator install.
        // More's menu is rendered only after loading finishes, so wait for it
        // instead of racing the network and reporting a false UI failure.
        compose.waitUntil(timeoutMillis = 60_000) {
            compose.onAllNodesWithTag("backstage-more-7")
                .fetchSemanticsNodes().isNotEmpty()
        }
        captureAppScreen("more")
        compose.onNodeWithTag("backstage-more-7").performClick()
        captureAppScreen("info")
        val screen = compose.onRoot().getUnclippedBoundsInRoot()
        val photo = compose.onNodeWithTag("backstage-fullscreen-start-photo")
            .assertExists()
            .getUnclippedBoundsInRoot()
        assertTrue("Photo should span full screen width",
            (photo.right - photo.left) >= (screen.right - screen.left) * 0.98f)
        assertTrue("Photo should span full screen height",
            (photo.bottom - photo.top) >= (screen.bottom - screen.top) * 0.98f)
        compose.onNodeWithContentDescription("Agenda").performClick()
        compose.onNodeWithTag("backstage-fullscreen-start-photo").assertDoesNotExist()
    }
}
