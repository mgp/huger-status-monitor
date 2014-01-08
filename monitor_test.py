import unittest

from monitor import *


class FrequencyDistributionTest(unittest.TestCase):
  """Test case for Frequencies."""

  def setUp(self):
    self.freq_dist = FrequencyDistribution()

  def test_add_value(self):
    self.assertSequenceEqual([], self.freq_dist._freqs)

    self.freq_dist.add_value(0)
    self.assertSequenceEqual([1], self.freq_dist._freqs)
    self.freq_dist.add_value(0)
    self.assertSequenceEqual([2], self.freq_dist._freqs)

    self.freq_dist.add_value(3)
    self.assertSequenceEqual([2, 0, 0, 1], self.freq_dist._freqs)

    self.freq_dist.add_value(4)
    self.assertSequenceEqual([2, 0, 0, 1, 1], self.freq_dist._freqs)

  def test_compute_std_dev(self):
    self.assertIsNone(self.freq_dist.compute_std_dev())

    # This test data is from https://en.wikipedia.org/wiki/Standard_deviation.
    for value in (2, 4, 4, 4, 5, 5, 7, 9):
      self.freq_dist.add_value(value)
    self.assertEqual(2.0, self.freq_dist.compute_std_dev())


class TrackedPlayerTest(unittest.TestCase):
  def setUp(self):
    self.first_kills = 10
    self.first_connect_duration = 50
    self.player = TrackedPlayer(self.first_kills, self.first_connect_duration)

  def test_regress_connect_duration(self):
    updated_connect_duration = self.first_connect_duration - 1
    new_kills = self.player._get_new_kills(self.first_kills, updated_connect_duration)
    self.assertEqual(self.first_kills, new_kills)

  def test_regress_kills(self):
    updated_kills = self.first_kills - 1
    new_kills = self.player._get_new_kills(updated_kills, self.first_connect_duration)
    self.assertEqual(updated_kills, new_kills)

  def test_no_new_kills(self):
    updated_connect_duration = self.first_connect_duration + 10
    new_kills = self.player._get_new_kills(self.first_kills, updated_connect_duration)
    self.assertEqual(0, new_kills)

  def test_new_kills(self):
    expected_new_kills = 3
    updated_kills = self.first_kills + expected_new_kills
    updated_connect_duration = self.first_connect_duration + 10
    new_kills = self.player._get_new_kills(updated_kills, updated_connect_duration)
    self.assertEqual(expected_new_kills, new_kills)

  def test_update(self):
    # Create a distribution with a stddev of 2.0.
    self.player._new_kills_dist.add_value(1)
    self.player._new_kills_dist.add_value(5)
    stddev = self.player._new_kills_dist.compute_std_dev()
    self.assertEqual(2.0, stddev)

    # Update the player with new kills.
    expected_new_kills = 6
    updated_kills = self.first_kills + expected_new_kills
    updated_connect_duration = self.first_connect_duration + 5
    new_kills, num_stddevs = self.player.update(updated_kills, updated_connect_duration)
    # Assert these new kills and their fraction of the standard deviation.
    self.assertEqual(expected_new_kills, new_kills)
    self.assertEqual(3.0, num_stddevs)

    # Assert that the kills and the connection duration of the player were updated.
    self.assertEqual(updated_kills, self.player.kills)
    self.assertEqual(updated_connect_duration, self.player.connect_duration)
    # Assert that the distribution is unchanged.
    self.assertEqual(stddev, self.player._new_kills_dist.compute_std_dev())


class MonitorTest(unittest.TestCase):
  """Test case for Monitor."""

  def setUp(self):
    self.monitor = Monitor(None, -1, -1)

  def _assert_player_kills(self, player_kills, name, new_kills, num_stddevs):
    """Asserts the values in a PlayerKills instance."""
    self.assertIsNotNone(player_kills)
    self.assertEqual(name, player_kills.name)
    self.assertEqual(new_kills, player_kills.new_kills)
    self.assertEqual(num_stddevs, player_kills.num_stddevs)

  def test_no_new_kills_first_update(self):
    """Tests that _get_new_kills returns no new kills on the first update.

    Both an existing player and a new player have new kills, but this is the first update.
    """
    # Create two new players.
    player_name1 = 'player_name1'
    player_name2 = 'player_name2'
    player1 = Player(1, 60)
    player2 = Player(3, 60)
    updated_players = {player_name1: player1, player_name2: player2}

    all_player_kills, have_new_kills = self.monitor._get_new_kills(
        updated_players, True)
    # No new kills because first update.
    self.assertEqual(2, len(all_player_kills))
    self._assert_player_kills(all_player_kills[0], player_name1, 0, 0)
    self._assert_player_kills(all_player_kills[1], player_name2, 0, 0)
    self.assertFalse(have_new_kills)

  def test_no_new_kills(self):
    """Tests that _get_new_kills returns no new kills on a subsequent update.

    Both an existing player and a new player have no new kills.
    """
    # Add an existing player to the monitor.
    player_name1 = 'player_name1'
    player1_first_kills = 10
    player1_first_connect_duration = 200
    tracked_player1 = TrackedPlayer(player1_first_kills, player1_first_connect_duration)
    for new_kills in (2, 2, 3, 3):
      tracked_player1.add_new_kills(new_kills)
    self.monitor._players[player_name1] = tracked_player1

    # The existing player has no new kills.
    player1 = Player(player1_first_kills, player1_first_connect_duration + 5)
    # The new player has no kills.
    player_name2 = 'player_name2'
    player2 = Player(0, 30)
    updated_players = {player_name1: player1, player_name2: player2}

    all_player_kills, have_new_kills = self.monitor._get_new_kills(
        updated_players, False)
    # No new kills because first update.
    self.assertEqual(2, len(all_player_kills))
    self._assert_player_kills(all_player_kills[0], player_name1, 0, 0)
    self._assert_player_kills(all_player_kills[1], player_name2, 0, 0)
    self.assertFalse(have_new_kills)

  def test_existing_player_new_kills(self):
    """Tests that _get_new_kills returns new kills on a subsequent update.

    Only the existing player has new kills.
    """
    # Add an existing player to the monitor.
    player_name1 = 'player_name1'
    player1_first_kills = 10
    player1_first_connect_duration = 200
    tracked_player1 = TrackedPlayer(player1_first_kills, player1_first_connect_duration)
    for new_kills in (2, 2, 3, 3):
      tracked_player1.add_new_kills(new_kills)
    self.monitor._players[player_name1] = tracked_player1

    # The existing player has no new kills.
    player1_new_kills = 1
    player1 = Player(
        player1_first_kills + player1_new_kills, player1_first_connect_duration + 5)
    # The new player has no kills.
    player_name2 = 'player_name2'
    player2 = Player(0, 30)
    updated_players = {player_name1: player1, player_name2: player2}

    all_player_kills, have_new_kills = self.monitor._get_new_kills(
        updated_players, False)
    # No new kills because first update.
    self.assertEqual(2, len(all_player_kills))
    self._assert_player_kills(
        all_player_kills[0], player_name1, player1_new_kills, 2)
    self._assert_player_kills(all_player_kills[1], player_name2, 0, 0)
    self.assertTrue(have_new_kills)

  def test_new_player_new_kills(self):
    """Tests that _get_new_kills returns new kills on a subsequent update.

    Only the new player has new kills.
    """
    # Add an existing player to the monitor.
    player_name1 = 'player_name1'
    player1_first_kills = 10
    player1_first_connect_duration = 200
    tracked_player1 = TrackedPlayer(player1_first_kills, player1_first_connect_duration)
    for new_kills in (2, 2, 3, 3):
      tracked_player1.add_new_kills(new_kills)
    self.monitor._players[player_name1] = tracked_player1

    # The existing player has no new kills.
    player1 = Player(player1_first_kills, player1_first_connect_duration + 5)
    # The new player has kills.
    player_name2 = 'player_name2'
    player2 = Player(2, 30)
    updated_players = {player_name1: player1, player_name2: player2}

    all_player_kills, have_new_kills = self.monitor._get_new_kills(
        updated_players, False)
    # No new kills because first update.
    self.assertEqual(2, len(all_player_kills))
    self._assert_player_kills(all_player_kills[0], player_name1, 0, 0)
    self._assert_player_kills(all_player_kills[1], player_name2, player2.kills, 0)
    self.assertTrue(have_new_kills)

  def _assert_tracked_player(self, tracked_player, kills, connect_duration, new_kills_dist):
    """Asserts the values in a TrackedPlayer instance."""
    self.assertIsNotNone(tracked_player)
    self.assertEqual(kills, tracked_player.kills)
    self.assertEqual(connect_duration, tracked_player.connect_duration)
    self.assertSequenceEqual(new_kills_dist, tracked_player._new_kills_dist._freqs)

  def test_update_player_kills_first_update(self):
    """Tests that _update_player_kills updates the new kill distribution of players.

    Both players have new kills, but this is the first update.
    """
    player_name1 = 'player_name1'
    player_name2 = 'player_name2'
    kills1 = 1
    kills2 = 2
    connect_duration1 = 30
    connect_duration2 = 40
    updated_players = {
        player_name1: Player(kills1, connect_duration1),
        player_name2: Player(kills2, connect_duration2),
    }
    all_player_kills = [
        PlayerKills(player_name1, kills1, 0),
        PlayerKills(player_name2, kills2, 0),
    ]
    # This is the first update, so will not add to kill distribution.
    self.monitor._update_player_kills(updated_players, True, all_player_kills)

    self.assertEqual(2, len(self.monitor._players))
    # Assert that first player exists, but kill distribution is empty.
    tracked_player = self.monitor._players[player_name1]
    self._assert_tracked_player(tracked_player, kills1, connect_duration1, [])
    # Assert that second player exists, but kill distribution is empty.
    tracked_player = self.monitor._players[player_name2]
    self._assert_tracked_player(tracked_player, kills2, connect_duration2, [])

  def test_update_player_kills_not_first_update(self):
    """Tests that _update_player_kills updates the new kill distribution of players.

    An existing player and a new player have new kills, and this is not the first update.
    """
    # Add an existing player.
    player_name1 = 'player_name1'
    kills1 = 5
    connect_duration1 = 30
    tracked_player = TrackedPlayer(kills1, connect_duration1)
    self.monitor._players[player_name1] = tracked_player

    # Update contains existing player.
    new_kills1 = 2
    # Update also contains a new player.
    player_name2 = 'player_name2'
    kills2 = 1
    connect_duration2 = 10
    updated_players = {
        player_name1: Player(kills1, connect_duration1),
        player_name2: Player(kills2, connect_duration2),
    }
    all_player_kills = [
        PlayerKills(player_name1, new_kills1, 0),
        PlayerKills(player_name2, kills2, 0),
    ]
    # This is not the first update, so will add to kill distribution.
    self.monitor._update_player_kills(updated_players, False, all_player_kills)

    self.assertEqual(2, len(self.monitor._players))
    # Assert that existing player still exists, and kill distribution updated.
    tracked_player = self.monitor._players[player_name1]
    self._assert_tracked_player(tracked_player, kills1, connect_duration1, [0, 0, 1])
    # Assert that new player exists, and kill distribution updated.
    tracked_player = self.monitor._players[player_name2]
    self._assert_tracked_player(tracked_player, kills2, connect_duration2, [0, 1])

  def test_remove_disconnected_players(self):
    player_name1 = 'player_name1'
    player_name2 = 'player_name2'
    player_name3 = 'player_name3'
    self.monitor._players[player_name1] = TrackedPlayer(10, 11)
    self.monitor._players[player_name2] = TrackedPlayer(20, 21)

    updated_players = {player_name2: None, player_name3: None}
    self.monitor._remove_disconnected_players(updated_players)

  def test_rank_players_by_attr_empty(self):
    players = []

    name_getter = itemgetter(0)
    attr_getter = itemgetter(1)
    ranks_by_player = self.monitor._rank_players_by_attr(players, name_getter, attr_getter)
    self.assertDictEqual({}, ranks_by_player)

  def test_rank_players_by_attr_single(self):
    player_name = 'player_name'
    players = [(player_name, 100)]

    name_getter = itemgetter(0)
    attr_getter = itemgetter(1)
    ranks_by_player = self.monitor._rank_players_by_attr(players, name_getter, attr_getter)
    expected_ranks_by_player = {player_name: 1}
    self.assertDictEqual(expected_ranks_by_player, ranks_by_player)

  def test_rank_players_by_attr_multi(self):
    player_name1 = 'player_name1'
    player_name2 = 'player_name2'
    player_name3 = 'player_name3'
    player_name4 = 'player_name4'
    players = [
        (player_name1, 150), (player_name2, 200), (player_name3, 150), (player_name4, 100)
    ]

    name_getter = itemgetter(0)
    attr_getter = itemgetter(1)
    ranks_by_player = self.monitor._rank_players_by_attr(players, name_getter, attr_getter)
    expected_ranks_by_player = {
        player_name1: 2,
        player_name2: 1,
        player_name3: 2,
        player_name4: 4
    }
    self.assertDictEqual(expected_ranks_by_player, ranks_by_player)

  def test_joint_rank(self):
    # Create three players.
    player_name1 = 'player_name1'
    player_name2 = 'player_name2'
    player_name3 = 'player_name3'
    # Kill ranks and stddev ranks are inverses.
    kill_ranks = {player_name1: 1, player_name2: 2, player_name3: 3}
    stddev_ranks = {player_name1: 3, player_name2: 2, player_name3: 1}

    # Weight kill ranks more.
    self.monitor.set_stddev_weight(25)
    joint_ranks = self.monitor._joint_rank(kill_ranks, stddev_ranks)
    self.assertDictEqual(kill_ranks, joint_ranks)

    # Weight stddev ranks more.
    self.monitor.set_stddev_weight(75)
    joint_ranks = self.monitor._joint_rank(kill_ranks, stddev_ranks)
    self.assertDictEqual(stddev_ranks, joint_ranks)

    # Weight both ranks equally.
    self.monitor.set_stddev_weight(50)
    joint_ranks = self.monitor._joint_rank(kill_ranks, stddev_ranks)
    expected_ranks = {player_name1: 1, player_name2: 1, player_name3: 1}
    self.assertDictEqual(expected_ranks, joint_ranks)

  def test_rank_players(self):
    # Create three players.
    player_name1 = 'player_name1'
    player_name2 = 'player_name2'
    player_name3 = 'player_name3'
    # Kill ranks and stddev ranks are inverses.
    player_kills = [
        PlayerKills(player_name1, 3, 1),
        PlayerKills(player_name2, 2, 2),
        PlayerKills(player_name3, 1, 3)
    ]

    # Rank by kills.
    self.monitor.set_stddev_weight(0)
    player_ranks = self.monitor._rank_players(player_kills)
    expected_player_ranks = {
        player_name1: 1,
        player_name2: 2,
        player_name3: 3
    }
    self.assertDictEqual(expected_player_ranks, player_ranks)

    # Rank by stddev.
    self.monitor.set_stddev_weight(100)
    player_ranks = self.monitor._rank_players(player_kills)
    expected_player_ranks = {
        player_name1: 3,
        player_name2: 2,
        player_name3: 1
    }
    self.assertDictEqual(expected_player_ranks, player_ranks)

    # Joint rank.
    self.monitor.set_stddev_weight(50)
    player_ranks = self.monitor._rank_players(player_kills)
    expected_player_ranks = {
        player_name1: 1,
        player_name2: 1,
        player_name3: 1
    }
    self.assertDictEqual(expected_player_ranks, player_ranks)


if __name__ == '__main__':
  unittest.main()

