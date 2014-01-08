from collections import namedtuple
import itertools
import math
from operator import itemgetter, attrgetter

from SourceQuery import SourceQuery


class FrequencyDistribution(object):
  """A frequency distribution over a collection of values."""

  def __init__(self):
    self._freqs = []

  def add_value(self, value):
    """Increments the frequency of the given value."""

    value = int(value)
    if value >= len(self._freqs):
      # Must extend the array so value is a valid index.
      elements_added = value + 1 - len(self._freqs)
      self._freqs.extend(elements_added * [0])
    self._freqs[value] += 1

  def compute_std_dev(self):
    """Computes the standard deviation of all values."""

    if not self._freqs:
      return None

    # First compute the mean.
    num_values = float(sum(self._freqs))
    values_sum = sum(i * freq for i, freq in enumerate(self._freqs))
    mean = values_sum / num_values
    # Use the mean to compute the standard deviation.
    values_sum_of_squares = sum(
        math.pow(i - mean, 2) * freq for i, freq in enumerate(self._freqs))
    std_dev = math.sqrt(values_sum_of_squares / num_values)
    return std_dev


class Player(object):
  """Information about a player."""

  def __init__(self, kills, connect_duration):
    self._kills = kills
    self._connect_duration = connect_duration

  @property
  def kills(self):
    return self._kills
  @property
  def connect_duration(self):
    return self._connect_duration


class TrackedPlayer(Player):
  """Information about a tracked player."""

  def __init__(self, kills, connect_duration):
    Player.__init__(self, kills, connect_duration)

    self._new_kills_dist = FrequencyDistribution()
    # Don't add kills to distribution.

  def _get_new_kills(self, updated_kills, updated_connect_duration):
    """Returns the number of kills by this player in the last interval."""

    if updated_connect_duration < self._connect_duration:
      # The player reconnected, so all kills are in this interval.
      return updated_kills
    elif updated_kills < self._kills:
      # The player's score was reset to 0, so all kills are in this interval.
      return updated_kills
    else:
      return updated_kills - self._kills

  def _get_num_stddevs(self, new_kills):
    stddev = self._new_kills_dist.compute_std_dev()
    if stddev is None:
      return 0
    return new_kills / stddev

  def update(self, updated_kills, updated_connect_duration):
    """Updates this player."""
    new_kills = self._get_new_kills(updated_kills, updated_connect_duration)
    num_stddevs = self._get_num_stddevs(new_kills)

    self._kills = updated_kills
    self._connect_duration = updated_connect_duration

    return new_kills, num_stddevs

  def add_new_kills(self, new_kills):
    """Adds the new kills to the distribution of new kills."""
    self._new_kills_dist.add_value(new_kills)


PlayerKills = namedtuple('PlayerKills', ['name', 'new_kills', 'num_stddevs'])
PlayerRank = namedtuple('PlayerRank', ['rank', 'player_objs'])


class Monitor(object):
  def __init__(self, host, port, interval_secs):
    self._source_query = SourceQuery(host, port)
    self._interval_secs = interval_secs
    self._players = {}

  """Weight for standard deviation is in [0, 100]."""
  _MAX_STDDEV_WEIGHT = 100

  def set_stddev_weight(self, stddev_weight):
    self._stddev_weight = stddev_weight

  def _get_new_kills(self, updated_players, first_update):
    """Returns a PlayerKills instance for each updated player.

    Parameter updated_players is the map of player names to Player instances in
    this update.
    Parameter first_update specifies whether this is the first update.

    Returns a pair of elements.
    The first element is a sequence of PlayerKill instances for each player.
    The second element specifies whether any player had new kills.
    """
    all_player_kills = []
    have_new_kills = False
    for updated_player_name, updated_player in updated_players.iteritems():
      curr_player = self._players.get(updated_player_name, None)
      if curr_player != None:
        # Update an existing player.
        new_kills, num_stddevs = curr_player.update(
            updated_player.kills, updated_player.connect_duration)
        if new_kills:
          have_new_kills = True
        all_player_kills.append(
            PlayerKills(updated_player_name, new_kills, num_stddevs))
      else:
        new_kills = 0
        if not first_update and updated_player.kills:
          # Do not count kills in the first update as new kills.
          new_kills = updated_player.kills
          have_new_kills = True
        all_player_kills.append(PlayerKills(updated_player_name, new_kills, 0))

    return all_player_kills, have_new_kills

  def _update_player_kills(self, updated_players, first_update, all_player_kills):
    """Updates the new kill distribution for each player.

    Parameter updated_players is the map of player names to Player instances in
    this update.
    Parameter first_update specifies whether this is the first update.
    Parameter all_player_kills is an array of PlayerKill instances for each player
    in the update.
    """
    for player_kills in all_player_kills:
      curr_player = self._players.get(player_kills.name, None)
      if curr_player != None:
        # Add the new kills to the distribution of an existing player.
        curr_player.add_new_kills(player_kills.new_kills)
      else:
        new_player = updated_players[player_kills.name]
        tracked_player = TrackedPlayer(new_player.kills, new_player.connect_duration)
        self._players[player_kills.name] = tracked_player
        if not first_update:
          tracked_player.add_new_kills(player_kills.new_kills)

  def _remove_disconnected_players(self, updated_players):
    """Removes all disconnected players."""
    removed_player_names = [player_name for player_name in self._players
        if player_name not in updated_players]
    for removed_player_name in removed_player_names:
      del self._players[removed_player_name]

  def _update_players(self, updated_players):
    """Updates each player, given an update from the server.

    Parameter updated_players is the map of player names to Player instances in
    this update.

    Returns an array of PlayerKill instances for each player in the update.
    """
    # Get the number of new kills for each updated player.
    first_update = not bool(self._players)
    all_player_kills, have_new_kills = self._get_new_kills(updated_players, first_update)

    if not have_new_kills:
      # The game is paused or there is a stalemate.
      return None
    self._update_player_kills(updated_players, first_update, all_player_kills)
    self._remove_disconnected_players(updated_players)

    # Return the new kills for each updated player for ranking.
    return all_player_kills

  def _rank_players_by_attr(self, player_objs, name_getter, attr_getter):
    """Ranks players by a specified attribute.

    Parameter player_objs is a sequence of objects representing the players.
    Parameter name_getter is a function that returns the player name.
    Parameter attr_getter is a function that returns the player attribute.

    Returns a map from each player name to its rank, starting at 1.
    """
    player_objs = sorted(player_objs, key=attr_getter, reverse=True)

    player_ranks = []
    prev_attr_value = None
    prev_rank = None
    for i, player_obj in enumerate(player_objs, start=1):
      attr_value = attr_getter(player_obj)
      if attr_value == prev_attr_value:
        # This player has a rank equal to the preceding player.
        prev_rank.player_objs.append(player_obj)
      else:
        # This player has a lesser rank than the preceding player.
        if prev_rank != None:
          player_ranks.append(prev_rank)
        prev_attr_value = attr_value
        prev_rank = PlayerRank(i, [player_obj])
    # Append the players with the least rank.
    if prev_rank != None:
      player_ranks.append(prev_rank)

    # Map each player name to its rank.
    ranks_by_player = {}
    for player_rank in player_ranks:
      for player_obj in player_rank.player_objs:
        ranks_by_player[name_getter(player_obj)] = player_rank.rank
    return ranks_by_player

  def _joint_rank(self, kill_ranks, stddev_ranks):
    """Returns the joint ranking of players.

    Parameter kill_ranks is a map from each player name to its ranking by kill.
    Parameter stddev_ranks is a map from each player name to its ranking by stddev.

    Returns a sequence of pairs, where each pair contains a player name and its
    joint rank.
    """
    num_players = len(kill_ranks)
    kill_weight = Monitor._MAX_STDDEV_WEIGHT - self._stddev_weight
    joint_ranks = []
    for player_name, kill_rank in kill_ranks.iteritems():
      stddev_rank = stddev_ranks[player_name]
      weighted_kill_rank = kill_weight * (num_players + 1 - kill_rank)
      weighted_stddev_rank = self._stddev_weight * (num_players + 1 - stddev_rank)
      weighted_total = weighted_kill_rank + weighted_stddev_rank

      joint_ranks.append((player_name, weighted_total))

    # Now rank each player by its joint ranking.
    name_getter = itemgetter(0)
    joint_rank_getter = itemgetter(1)
    return self._rank_players_by_attr(joint_ranks, name_getter, joint_rank_getter)

  def _rank_players(self, player_kills):
    """Returns the ranking of players.

    Parameter player_kills is a sequence of PlayerKill instances.

    Returns a map from each player name to its rank.
    """
    name_getter = attrgetter('name')
    kill_getter = attrgetter('new_kills')
    stddev_getter = attrgetter('num_stddevs')

    if self._stddev_weight == 0:
      return self._rank_players_by_attr(player_kills, name_getter, kill_getter)
    elif self._stddev_weight == Monitor._MAX_STDDEV_WEIGHT:
      return self._rank_players_by_attr(player_kills, name_getter, stddev_getter)
    else:
      # Rank each player by kill and also by stddev. Then compute each joint rank.
      kill_ranks = self._rank_players_by_attr(player_kills, name_getter, kill_getter)
      stddev_ranks = self._rank_players_by_attr(player_kills, name_getter, stddev_getter)
      return self._joint_rank(kill_ranks, stddev_ranks)

  def update(self):
    try:
      updated_players = {
          player['name']: Player(player['kills'], player['time'])
            for player in source_query.player()
      }
    except:
      return None

    player_kills = self._update_players(updated_players)
    if player_kills is None:
      return None
    return self._rank_players(player_kills)

