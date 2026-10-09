"""Focused checks for the saved-loss-only exploratory extractor."""

from pathlib import Path
import runpy

import numpy as np
import pytest

threshold_counts = runpy.run_path(str(Path(__file__).resolve().parents[1] / "exploratory/reproducibility_frontier.py"))["threshold_counts"]


def test_tolerance_boundary_is_inclusive_and_complements_strict_exceedance():
    losses = np.array([0, .001, .0025, .005, .01, .010001])
    thresholds = [0, 10, 25, 50, 100]
    counts = threshold_counts(losses, thresholds)
    np.testing.assert_array_equal(counts, [1, 2, 3, 4, 5])
    np.testing.assert_array_equal(counts, len(losses) - (losses[:, None] > np.array(thresholds)[None, :] / 10000).sum(axis=0))
    assert (np.diff(counts) >= 0).all()


@pytest.mark.parametrize("losses", [[], [np.nan], [np.inf], [-.001]])
def test_invalid_saved_losses_fail_loudly(losses):
    with pytest.raises(ValueError):
        threshold_counts(losses)


def test_zero_loss_counts_even_if_a_tie_changes_the_reported_label():
    # The frontier concerns CEQ loss, not winner-label switching.
    np.testing.assert_array_equal(threshold_counts([0, .001], [0]), [1])
