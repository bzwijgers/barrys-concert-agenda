package com.example.barrysconcertagenda

import androidx.activity.ComponentActivity
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsSelected
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.getUnclippedBoundsInRoot
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTouchInput
import androidx.compose.ui.test.swipeLeft
import androidx.test.ext.junit.runners.AndroidJUnit4
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

    @Test fun welcomeScreenOpensFiveMainIconsAndMore() {
        compose.onNodeWithContentDescription("Barry's concert agenda").performClick()
        for (item in listOf("Home", "Ontdek", "Agenda", "Mijn tickets", "Favorieten", "Meer")) {
            compose.onNodeWithContentDescription(item).assertIsDisplayed()
        }
        compose.onNodeWithContentDescription("Favorieten").performClick()
        compose.onNodeWithContentDescription("Favorieten").assertIsSelected()
        compose.onNodeWithContentDescription("Agenda").performClick()
        compose.onNodeWithContentDescription("Agenda").assertIsSelected()
    }

    @Test fun swipingHomeMovesToDiscoverTab() {
        compose.onNodeWithContentDescription("Barry's concert agenda").performClick()
        compose.onNodeWithContentDescription("Home").assertIsSelected()
        compose.onRoot().performTouchInput { swipeLeft() }
        compose.onNodeWithContentDescription("Ontdek").assertIsSelected()
    }

    @Test fun startPhotoCoversFullPageAndSurvivesTabSwitch() {
        compose.onNodeWithContentDescription("Barry's concert agenda").performClick()
        val screen = compose.onRoot().getUnclippedBoundsInRoot()
        val photo = compose.onNodeWithTag("backstage-fullscreen-start-photo")
            .assertExists()
            .getUnclippedBoundsInRoot()
        assertTrue("Photo should span full screen width", photo.width >= screen.width * 0.98f)
        assertTrue("Photo should span full screen height", photo.height >= screen.height * 0.98f)
        compose.onNodeWithContentDescription("Ontdek").performClick()
        compose.onNodeWithTag("backstage-fullscreen-start-photo").assertExists()
    }
}
