import unittest
from scrapers.feed_quality import deduplicate_performances, is_known_nonconcert


def show(artist, date="2026-12-19", time="20:00",
         venue="Dynamo", city="Eindhoven",
         url="https://www.dynamo-eindhoven.nl/evenement/john-coffey"):
    return dict(artist=artist,date=date,time=time,venue=venue,city=city,url=url,source="Dynamo")


class FeedQualityTests(unittest.TestCase):
    def test_official_hall_wins_over_podiuminfo_same_show(self):
        official=show("John Coffey")
        index=show("John Coffey", url="https://www.podiuminfo.nl/concert/480239/John-Coffey/Dynamo")
        distinct, removed=deduplicate_performances([official,index])
        self.assertEqual(distinct,[official])
        self.assertEqual(removed,[index])
        distinct, removed=deduplicate_performances([index,official])
        self.assertEqual(distinct,[official])

    def test_half_hour_start_difference_from_aggregator_is_not_second_concert(self):
        official=show("Half Me",time="19:00")
        index=show("Half Me",time="19:30",url="https://www.podiuminfo.nl/concert/480632/Half-Me/Dynamo")
        distinct,removed=deduplicate_performances([official,index])
        self.assertEqual(distinct,[official])
        self.assertEqual(len(removed),1)

    def test_keep_actual_two_performances_same_day_different_times(self):
        afternoon=show("Sam Bettens",time="16:00",city="Breda",venue="MEZZ",
                       url="https://www.mezz.nl/programma/sam-bettens-2/")
        evening=show("Sam Bettens",time="20:30",city="Breda",venue="MEZZ",
                     url="https://www.mezz.nl/programma/sam-bettens/")
        distinct,removed=deduplicate_performances([afternoon,evening])
        self.assertEqual(distinct,[afternoon,evening])
        self.assertEqual(len(removed),0)

    def test_two_different_concerts_same_stage_day_survive(self):
        first=show("A Band")
        second=show("B Band")
        distinct,_=deduplicate_performances([first,second])
        self.assertEqual(len(distinct),2)

    def test_same_artist_date_venue_and_time_different_ticket_link_is_one_show(self):
        one=show("Gotu Jim",city="Rotterdam",venue="Maassilo",url="https://www.rotown.nl/agenda/gotu-jim-1/")
        two=show("Gotu Jim",city="Rotterdam",venue="Maassilo",url="https://bird-rotterdam.nl/event/gotu-jim")
        distinct,removed=deduplicate_performances([one,two])
        self.assertEqual(distinct,[one])
        self.assertEqual(removed,[two])

    def test_nonconcert_filter_specific_no_false_positive_on_live_music(self):
        for name in ("90's NOW", "Fiesta Macumba", "Cheeky Monday: DJ",
                     "Muziek Bingo XXL", "Qmusic the Party - 4 uur fout",
                     "Jimmy Carr: Laughs Funny"):
            self.assertTrue(is_known_nonconcert(show(name)), name)
        for name in ("Bloc Party + Interpol", "Niall Horan: Dinner Party Live On Tour",
                     "Dave Clarke Presents: 30 Years of ADE", "Mogwai",
                     "30 Jaar Excelsior Recordings", "Jill Scott"):
            self.assertFalse(is_known_nonconcert(show(name)), name)


if __name__ == "__main__":
    unittest.main()
