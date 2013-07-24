import itertools
import math


class Weight:
  """A weight that adjusts a player score."""

  def __init__(self, scale_factor):
    self.scale_factor = scale_factor

  def adjust_score(self, score):
    return self.scale_factor * score


class FrequencyDistribution:
  """A frequency distribution over a collection of values."""

  def __init__(self):
    self.freqs = []

  def add_value(self, value):
    """Increments the frequency of the given value."""
    value = int(value)
    if value >= len(self.freqs):
      # Must extend the array so value is a valid index.
      elements_added = value + 1 - len(self.freqs)
      self.freqs.extend(elements_added * [0])
    self.freqs[value] += 1

  def compute_std_dev(self):
    """Computes the standard deivation of all values."""
    if not self.freqs:
      return None

    # First compute the mean.
    num_values = float(sum(self.freqs))
    values_sum = sum(i * freq for i, freq in enumerate(self.freqs))
    mean = values_sum / num_values
    # Use the mean to compute the standard deviation.
    values_sum_of_squares = sum(
        math.pow(i - mean, 2) * freq for i, freq in enumerate(self.freqs))
    std_dev = math.sqrt(values_sum_of_squares / num_values)
    return std_dev


class Monitor:
  ONLY_NUM_FRAGS = 0
  MOST_NUM_FRAGS = 1
  SPLIT = 2
  MOST_TIME_LAST_FRAG = 3
  ONLY_TIME_LAST_FRAG = 4

  EXCLUDE = Weight(0)
  LOW = Weight(0.5)
  NORMAL = Weight(1)
  HIGH = Weight(1.5)

  def __init__(self, address, port, interval_secs):
    self.address = address
    self.port = port
    self.interval_secs = interval_secs

    self.player_weights = {}
    self.poll_num = 0

    self.prev_player_frags = {}
    self.prev_player_frag_intervals = {}

  def update_player_weights(self, curr_player_scores):
    # Delete players that have disconnected.
    # Use keys() so we can delete from player_weights as we iterate.
    for player_name in player_weights.keys():
      if player_name not in curr_player_scores:
        del player_weights[player_name]

    # Add players that have connected.
    for player_name in curr_player_scores:
      player_weights.setdefault(player_name, Monitor.NORMAL)

  def stop(self):
    pass

  def apply_player_weights(self, player_scores):
    # Use items() so we can modify player_scores as we iterate
    for player_name, score in player_scores.items():
      weight = self.player_weights.get(player_name, Monitor.NORMAL)
      player_scores[player_name] = weight.adjust_score(score)

  def get_frags_added(self, curr_player_frags):
    """Returns the frags added by each player since the the last poll.
    """
    frags_added_by_player = {}
    for player_name, curr_frags in curr_player_frags.iteritems():
      prev_frags = self.prev_player_frags.get(player_name, 0)
      if curr_frags >= prev_frags:
        frags_added = curr_frags - prev_frags
      else:
        # Player reconnected or score was reset to 0.
        frags_added = curr_frags

      if frags_added:
        frags_added_by_player[player_name] = frags_added
    return frags_added_by_player
    
  def get_intervals_since_last_frag(self, frags_added_by_player):
    # TODO
    pass

