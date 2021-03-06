from itertools import chain

from datetime import timedelta

from wanikani_api.models import Vocabulary, Reading, Meaning
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import HttpResponseForbidden
from django.test import Client
from django.utils import timezone
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from kw_webapp import constants
from kw_webapp.models import MeaningSynonym, UserSpecific, Profile, Tag
from kw_webapp.tests import sample_api_responses_v2
from kw_webapp.tests.utils import (
    create_user,
    create_review,
    create_reading,
    create_profile,
)
from kw_webapp.tests.utils import create_vocab


class TestModels(APITestCase):
    def setUp(self):
        self.user = create_user("Tadgh")
        self.user.set_password("password")
        create_profile(self.user, "any key", 1)
        self.user.save()
        self.vocabulary = create_vocab("cat")
        self.review = create_review(self.vocabulary, self.user)
        self.review.meaning_synonyms.get_or_create(text="minou")

        # default state of a test is a user that has a single review, and the review has a single synonym added.

    def test_toggling_review_hidden_ownership_fails_on_wrong_user(self):
        user2 = create_user("eve")
        user2.set_password("im_a_hacker")
        create_profile(user2, "any_key", 1)
        user2.save()
        relevant_review_id = UserSpecific.objects.get(
            user=self.user, vocabulary=self.vocabulary
        ).id

        self.client.force_login(user2)
        response = self.client.post(
            reverse("api:review-hide", args=(relevant_review_id,))
        )
        self.assertIsInstance(response, HttpResponseForbidden)

    def test_toggling_review_hidden_ownership_works(self):
        relevant_review_id = UserSpecific.objects.get(
            user=self.user, vocabulary=self.vocabulary
        ).id
        before_toggle_hidden = UserSpecific.objects.get(
            id=relevant_review_id
        ).hidden

        if self.client.login(username=self.user.username, password="password"):
            response = self.client.post(
                path="/kw/togglevocab/", data={"review_id": relevant_review_id}
            )
            print(response.content)
        else:
            self.fail("Couldn't log in!?")

        after_toggle_hidden = UserSpecific.objects.get(id=relevant_review_id)
        self.assertNotEqual(before_toggle_hidden, after_toggle_hidden)

    def test_adding_synonym_works(self):
        self.review.meaning_synonyms.get_or_create(text="une petite chatte")
        self.assertEqual(2, len(self.review.meaning_synonyms.all()))

    def test_removing_synonym_by_lookup_works(self):
        remove_text = "minou"
        self.review.remove_synonym(remove_text)
        self.assertNotIn(remove_text, self.review.synonyms_list())

    def test_removing_nonexistent_synonym_fails(self):
        remove_text = "un chien"
        self.assertRaises(
            MeaningSynonym.DoesNotExist,
            self.review.remove_synonym,
            remove_text,
        )

    def test_removing_synonym_by_object_works(self):
        synonym, created = self.review.meaning_synonyms.get_or_create(
            text="minou"
        )
        self.review.meaning_synonyms.remove(synonym)

    def test_reading_clean_fails_with_invalid_levels_too_high(self):
        v = create_vocab("cat")
        r = create_reading(v, "ねこ", "ねこ", 61)

        self.assertRaises(ValidationError, r.clean_fields)

    def test_reading_clean_fails_with_invalid_levels_too_low(self):
        v = create_vocab("cat")
        r = create_reading(v, "ねこ", "ねこ", 0)

        self.assertRaises(ValidationError, r.clean_fields)

    def test_vocab_number_readings_is_correct(self):
        create_reading(self.vocabulary, "ねこ", "ねこ", 2)
        create_reading(self.vocabulary, "ねこな", "猫", 1)
        self.assertEqual(self.vocabulary.reading_count(), 2)

    def test_synonym_adding(self):
        self.review.meaning_synonyms.get_or_create(text="kitty")

        self.assertIn("kitty", self.review.synonyms_string())

    def test_get_all_readings_returns_original_and_added_readings(self):
        self.vocabulary.readings.create(kana="what", character="ars", level=5)
        self.review.reading_synonyms.create(kana="shwoop", character="fwoop")

        expected = list(
            chain(
                self.vocabulary.readings.all(),
                self.review.reading_synonyms.all(),
            )
        )

        self.assertListEqual(expected, self.review.get_all_readings())

    def test_setting_twitter_account_correctly_prepends_at_symbol(self):
        non_prepended_account_name = "Tadgh"
        self.user.profile.set_twitter_account(non_prepended_account_name)

        users_profile = Profile.objects.get(user=self.user)
        self.assertEqual(users_profile.twitter, "@Tadgh")

    def test_setting_twitter_account_works_when_input_is_already_valid(self):
        account_name = "@Tadgh"
        self.user.profile.set_twitter_account(account_name)

        users_profile = Profile.objects.get(user=self.user)

        self.assertEqual(users_profile.twitter, "@Tadgh")

    def test_setting_an_invalid_twitter_handle_does_not_modify_model_instance(
        self
    ):
        invalid_account_name = "!!"
        old_twitter = self.user.profile.twitter

        self.user.profile.set_twitter_account(invalid_account_name)

        users_profile = Profile.objects.get(user=self.user)

        self.assertEqual(users_profile.twitter, old_twitter)

    def test_setting_a_blank_twitter_handle_does_not_modify_model_instance(
        self
    ):
        invalid_account_name = "@"
        old_twitter = self.user.profile.twitter

        self.user.profile.set_twitter_account(invalid_account_name)

        users_profile = Profile.objects.get(user=self.user)

        self.assertEqual(users_profile.twitter, old_twitter)

    def test_setting_valid_profile_website_modifies_model(self):
        valid_site = "www.kaniwani.com"

        self.user.profile.set_website(valid_site)

        users_profile = Profile.objects.get(user=self.user)

        self.assertEqual(users_profile.website, valid_site)

    def test_setting_website_with_http_prepended_gets_it_stripped(self):
        http_prepended_valid_site = "http://https://www.kaniwani.com"

        self.user.profile.set_website(http_prepended_valid_site)

        users_profile = Profile.objects.get(user=self.user)

        self.assertEqual(users_profile.website, "www.kaniwani.com")

    def test_protocol_only_strings_are_rejected_when_setting_website(self):
        invalid_url = "http://"
        old_url = self.user.profile.website

        self.user.profile.set_website(invalid_url)

        users_profile = Profile.objects.get(user=self.user)
        self.assertEqual(users_profile.website, old_url)

    def test_website_setting_on_None_site(self):
        invalid_url = None
        old_url = self.user.profile.website

        self.user.profile.set_website(invalid_url)

        users_profile = Profile.objects.get(user=self.user)
        self.assertEqual(users_profile.website, old_url)

    def test_setting_twitter_on_none_twitter(self):
        twitter_handle = None
        old_twitter = self.user.profile.twitter

        self.user.profile.set_twitter_account(twitter_handle)

        users_profile = Profile.objects.get(user=self.user)
        self.assertEqual(old_twitter, users_profile.twitter)

    def test_rounding_a_review_time_follows_wk_rules(self):
        self.review.streak = 0
        self.review.next_review_date = self.review.next_review_date.replace(
            hour=10
        )
        self.review.next_review_date = self.review.next_review_date.replace(
            minute=17
        )
        self.review.save()
        self.review.refresh_from_db()

        self.review._round_next_review_date()
        self.review.refresh_from_db()
        self.assertEqual(self.review.next_review_date.minute, 0)
        self.assertEqual(self.review.next_review_date.hour, 10)

        self.review.answered_correctly(first_try=True, can_burn=True)
        self.review.refresh_from_db()
        current_hour = timezone.now().hour

        self.assertEqual(self.review.next_review_date.minute, 0)
        self.assertEqual(
            self.review.next_review_date.hour, (current_hour + 4) % 24
        )

    def test_rounding_up_a_review_rounds_up_last_studied_date(self):
        self.review.last_studied = timezone.now()
        self.review.last_studied = self.review.last_studied.replace(minute=17)
        self.review._round_review_time_up()

        self.assertEqual(
            self.review.last_studied.minute
            % (constants.REVIEW_ROUNDING_TIME.total_seconds() / 60),
            0,
        )

    def test_default_review_times_are_not_rounded(self):
        rounded_time = self.review.next_review_date
        new_vocab = create_review(create_vocab("fresh"), self.user)

        self.assertNotEqual(rounded_time, new_vocab.next_review_date)

    def test_handle_wanikani_level_up_correctly_levels_up(self):
        old_level = self.user.profile.level

        self.user.profile.handle_wanikani_level_change(
            self.user.profile.level + 1
        )
        self.user.refresh_from_db()

        self.assertEqual(self.user.profile.level, old_level + 1)

    def test_updating_next_review_date_based_on_last_studied_works(self):
        current_time = timezone.now()
        self.review.last_studied = current_time
        self.review.streak = 4
        delta_hours = constants.SRS_TIMES[4]
        future_time = current_time + timedelta(hours=delta_hours)

        self.review.save()

        self.review.set_next_review_time_based_on_last_studied()

        self.review.refresh_from_db()

        self.assertTrue(
            self.review.next_review_date - future_time < timedelta(minutes=15)
        )

    def test_tag_search_works(self):
        vocab = create_vocab("spicy meatball")
        vocab2 = create_vocab("spicy pizza")

        reading = create_reading(vocab, "SOME_READING", "SOME_CHARACTER", 5)
        reading2 = create_reading(
            vocab2, "SOME_OTHER_READING", "SOME_OTHER_CHARACTER", 5
        )

        spicy_tag = Tag.objects.create(name="spicy")

        reading.tags.add(spicy_tag)
        reading2.tags.add(spicy_tag)

        reading.save()
        reading2.save()

        spicy_tag.refresh_from_db()
        spicy_vocab = spicy_tag.get_all_vocabulary()

        self.assertTrue(spicy_vocab.count() == 2)

    def test_vocabulary_that_has_multiple_readings_with_same_tag_appears_only_once(
        self
    ):
        vocab = create_vocab("spicy meatball")

        reading = create_reading(vocab, "SOME_READING", "SOME_CHARACTER", 5)
        reading2 = create_reading(
            vocab, "SOME_OTHER_READING", "SOME_OTHER_CHARACTER", 5
        )

        spicy_tag = Tag.objects.create(name="spicy")

        reading.tags.add(spicy_tag)
        reading2.tags.add(spicy_tag)

        reading.save()
        reading2.save()

        spicy_tag.refresh_from_db()
        spicy_vocab = spicy_tag.get_all_vocabulary()

        self.assertEqual(spicy_vocab.count(), 1)

    def test_adding_notes_to_reviews_works(self):
        self.assertTrue(self.review.notes is None)

        self.review.notes = "This is a note for my review!"
        self.review.save()

        self.assertTrue(self.review.notes is not None)

    def test_tag_names_are_unique(self):
        Tag.objects.create(name="S P I C Y")
        self.assertRaises(IntegrityError, Tag.objects.create, name="S P I C Y")

    def test_setting_criticality_of_review(self):
        self.review.correct = 1
        self.review.incorrect = 2
        self.review.save()
        self.review.refresh_from_db()

        self.assertFalse(self.review.critical)

        self.review.answered_incorrectly()

        self.assertTrue(self.review.critical)

    def test_critical_not_set_when_below_attempt_threshold(self):
        self.review.correct = 0
        self.review.incorrect = 1
        self.review.save()
        self.review.refresh_from_db()

        self.assertFalse(self.review.critical)

        # Brings total attempt count to 2
        self.review.answered_incorrectly()

        self.assertFalse(self.review.critical)

    def test_review_correctly_comes_out_of_critical_once_guru(self):
        self.review.correct = 1
        self.review.incorrect = 3
        self.review.critical = True
        self.review.save()
        self.review.refresh_from_db()

        self.assertTrue(self.review.critical)

        self.review.answered_correctly(first_try=True, can_burn=True)

        self.review.refresh_from_db()
        self.assertFalse(self.review.critical)

    def test_newly_created_user_specific_has_null_last_studied_date(self):
        review = create_review(create_vocab("test"), self.user)
        self.assertIsNone(review.last_studied)

    def test_vocabulary_should_be_updated(self):
        self.vocabulary.parts_of_speech.get_or_create(part="verb")
        self.vocabulary.parts_of_speech.get_or_create(part="out_of_date")
        self.vocabulary.alternate_meanings = "out_of_date"
        self.vocabulary.readings.get_or_create(
            kana="current_kana", character="current_character", level=1
        )
        self.vocabulary.readings.get_or_create(
            kana="outdated_kana", character="outdated_character", level=1
        )
        self.vocabulary.readings.get_or_create(
            kana="outdated_kana2", character="outdated_character2", level=1
        )
        self.vocabulary.save()
        self.vocabulary.refresh_from_db()

        fake_new_vocab = Vocabulary(
            json_data=sample_api_responses_v2.single_vocab_v2
        )

        assert self.vocabulary.is_out_of_date(fake_new_vocab)
        self.vocabulary.reconcile(fake_new_vocab)

        self.vocabulary.refresh_from_db()

        assert self.vocabulary.readings.count() == 2
        assert (
            self.vocabulary.readings.filter(kana="swanky new kana").count()
            == 1
        )
        assert (
            self.vocabulary.readings.filter(kana="current_kana").count() == 1
        )

        assert self.vocabulary.parts_of_speech.count() == 2
        assert (
            self.vocabulary.parts_of_speech.filter(part="out_of_date").count()
            == 0
        )
        assert self.vocabulary.parts_of_speech.filter(part="verb").count() == 1
        assert (
            self.vocabulary.parts_of_speech.filter(
                part="definitely a verb"
            ).count()
            == 1
        )
        #TODO UNCOMMENT THIS ONCE LOGIC IS FIXED
        #assert self.vocabulary.alternate_meanings == "secondary doesnt matter"

    def test_answered_correctly_can_burn(self):
        self.review.streak = constants.KANIWANI_SRS_LEVELS[
            constants.KwSrsLevel.ENLIGHTENED.name
        ][0]

        self.review.answered_correctly(first_try=True, can_burn=True)
        self.review.refresh_from_db()

        self.assertEqual(
            self.review.streak,
            constants.KANIWANI_SRS_LEVELS[constants.KwSrsLevel.BURNED.name][0],
        )
        self.assertTrue(self.review.burned)

    def test_answered_correctly_cannot_burn(self):
        enlightened_level = constants.KANIWANI_SRS_LEVELS[
            constants.KwSrsLevel.ENLIGHTENED.name
        ][0]
        self.review.streak = enlightened_level

        self.review.answered_correctly(first_try=True, can_burn=False)
        self.review.refresh_from_db()

        self.assertEqual(self.review.streak, enlightened_level)
        self.assertFalse(self.review.burned)
