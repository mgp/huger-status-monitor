import unittest

from monitor import *

class WeightTest(unittest.TestCase):
  """Test case for Weight."""

  def test_adjust_score(self):
    weight = Weight(0.0)
    self.assertEqual(0.0, weight.adjust_score(5.0))
    weight = Weight(1.0)
    self.assertEqual(5.0, weight.adjust_score(5.0))
    weight = Weight(2.0)
    self.assertEqual(10.0, weight.adjust_score(5.0))

class FrequencyDistributionTest(unittest.TestCase):
  """Test case for Frequencies."""

  def setUp(self):
    self.freq_dist = FrequencyDistribution()

  def test_add_value(self):
    self.assertSequenceEqual([], self.freq_dist.freqs)

    self.freq_dist.add_value(0)
    self.assertSequenceEqual([1], self.freq_dist.freqs)
    self.freq_dist.add_value(0)
    self.assertSequenceEqual([2], self.freq_dist.freqs)

    self.freq_dist.add_value(3)
    self.assertSequenceEqual([2, 0, 0, 1], self.freq_dist.freqs)

    self.freq_dist.add_value(4)
    self.assertSequenceEqual([2, 0, 0, 1, 1], self.freq_dist.freqs)

  def test_compute_std_dev(self):
    self.assertIsNone(self.freq_dist.compute_std_dev())

    # This test data is from https://en.wikipedia.org/wiki/Standard_deviation.
    for value in (2, 4, 4, 4, 5, 5, 7, 9):
      self.freq_dist.add_value(value)
    self.assertEqual(2.0, self.freq_dist.compute_std_dev())


class MonitorTest(unittest.TestCase):
  """Test case for Monitor."""

  def setUp(self):
    self.monitor = Monitor(None, -1, -1)

  def test_get_frags_added(self):
    prev_player_frags = {
        'disconnected1': 1,
        'disconnected2': 2,
        'increased3': 3,
        'increased4': 4,
    }
    self.monitor.prev_player_frags = prev_player_frags
    curr_player_frags = {
        'connected5': 5,
        'connected6': 6,
        'increased3': 7,
        'increased4': 9,
    }

    expected_frags_added_by_player = {
        'connected5': 5,
        'connected6': 6,
        'increased3': 4,
        'increased4': 5,
    }
    frags_added_by_player = self.monitor.get_frags_added(curr_player_frags)
    self.assertDictEqual(
        expected_frags_added_by_player, frags_added_by_player)

  def test_get_frags_added_omits_unchanged(self):
    prev_player_frags = {
        'unchanged1': 1,
        'unchanged2': 2,
    }
    self.monitor.prev_player_frags = prev_player_frags
    curr_player_frags = prev_player_frags

    frags_added_by_player = self.monitor.get_frags_added(curr_player_frags)
    self.assertDictEqual({}, frags_added_by_player)

  def test_get_frags_added_avoids_negative(self):
    prev_player_frags = {
        'decreased1': 5,
        'decreased2': 6
    }
    self.monitor.prev_player_frags = prev_player_frags
    curr_player_frags = {
        'decreased1': 4,
        'decreased2': 3,
    }

    frags_added_by_player = self.monitor.get_frags_added(curr_player_frags)
    self.assertDictEqual(curr_player_frags, frags_added_by_player)


if __name__ == '__main__':
  unittest.main()

