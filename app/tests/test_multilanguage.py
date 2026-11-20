"""Questions in other languages: the library is English, so the search runs in English and the answer comes back in the
person's language."""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import assistant                      # noqa: E402
from engine import lang               # noqa: E402

SAMPLES = {
    'ca': ['Com puc fer que l’aigua sigui potable si no tinc electricitat?', 'El meu fill té febre, quant paracetamol li puc donar?'],
    'es': ['¿Cómo puedo potabilizar el agua sin electricidad?', 'Mi hijo de 4 años tiene fiebre, cuánto paracetamol le doy?'],
    'fr': ["Comment rendre l'eau potable sans électricité ?"],
    'de': ['Wie kann ich Wasser ohne Strom trinkbar machen?'],
    'it': ["Come posso rendere potabile l'acqua senza elettricità?"],
    'pt': ['Como posso tornar a água potável sem eletricidade?'],
    'nl': ['Hoe kan ik water drinkbaar maken zonder stroom?'],
    'en': ['How do I make water safe to drink?', 'bleach dose', 'CPR on an adult, how deep?', 'Where is the nearest hospital?'],
}


class Detect(unittest.TestCase):
    def test_languages(self):
        for code, questions in SAMPLES.items():
            for q in questions:
                with self.subTest(q=q):
                    self.assertEqual(lang.detect(q), code)

    def test_short_or_empty_is_english(self):
        for q in ('', 'agua', 'hola amigo'):
            self.assertEqual(lang.detect(q), 'en')


class FakeLocal:
    def __init__(self, reply, running=True):
        self.reply, self.running, self.asked = reply, running, []

    def ensure_running(self, on_wait=None, cancelled=lambda: False):
        return None if self.running else 'The local AI is not set up on this computer.'

    def generate(self, segments, max_tokens, cancelled, on_text):
        self.asked.append((segments, max_tokens))
        on_text(self.reply)
        return {'ev': 'done', 'reason': 'eog'}


class EnglishQuery(unittest.TestCase):
    def ask(self, reply, running=True):
        fake = FakeLocal(reply, running)
        with mock.patch.object(assistant, 'LOCAL', fake), mock.patch.object(assistant, 'local_on', lambda: True):
            return assistant.english_query('Com puc fer que l’aigua sigui potable?', lambda: False, lambda ev: None), fake

    def test_first_line_cleaned(self):
        q, fake = self.ask(' "make water safe to drink without electricity"\nboil chlorine')
        self.assertEqual(q, 'make water safe to drink without electricity')
        segments, max_tokens = fake.asked[0]
        self.assertEqual(max_tokens, 48)                # a short generation, not a whole answer
        self.assertEqual(segments[-1], ['QUERY:', False])   # the reply is started for the model

    def test_repeats_after_stray_marks_are_cut(self):
        """E4B on a German question: the query, then stray closing marks and the query again."""
        q, _ = self.ask(' food refrigerator without power safe time<channel|>\n<channel|>\n<channel|>QUERY: food refrigerator')
        self.assertEqual(q, 'food refrigerator without power safe time')

    def test_narration_is_not_searched(self):
        """E4B without the started reply: a sentence about the task instead of a query."""
        q, _ = self.ask('The user wants me to convert a Catalan question ("How can I make water potable?") into a short English search query.')
        self.assertIsNone(q)

    def test_bare_key_words_are_accepted(self):
        q, _ = self.ask('purify drinking water no electricity')
        self.assertEqual(q, 'purify drinking water no electricity')

    def test_thinking_is_dropped(self):
        q, _ = self.ask(' purify drinking water<|channel>thought\nmore')
        self.assertEqual(q, 'purify drinking water')

    def test_no_model_means_search_as_typed(self):
        q, fake = self.ask('anything', running=False)
        self.assertIsNone(q)
        self.assertEqual(fake.asked, [])


if __name__ == '__main__':
    unittest.main()
