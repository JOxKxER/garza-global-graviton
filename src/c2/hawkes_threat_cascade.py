"""Hawkes self-exciting point process for cascading threat-tempo forecasting.

Tactical use: cyberattack bursts and artillery barrages are self-exciting --
each event temporarily raises the likelihood of the next one -- unlike a
memoryless Poisson process. Modeling historical event timestamps this way
lets a C2 system forecast the near-term intensity of an unfolding cascade
instead of assuming a flat average attack rate.
"""

import numpy as np


class HawkesThreatCascade:
    """Computes Hawkes process intensity from historical event timestamps."""

    def __init__(self, background_rate_mu, excitation_alpha, decay_beta):
        """Set the background rate mu, excitation alpha, and decay beta."""
        self.background_rate_mu = background_rate_mu
        self.excitation_alpha = excitation_alpha
        self.decay_beta = decay_beta

    def calc_intensity(self, evaluation_times, historical_event_times):
        """Evaluate lambda(t) = mu + sum_{ti<t} alpha*exp(-beta*(t-ti)).

        Tactical advantage: a single broadcasted pairwise-time-difference
        pass scores an array of evaluation times against the full event
        history at once, giving a live-updating threat-tempo forecast
        instead of a static historical average.
        """
        t = np.atleast_1d(np.asarray(evaluation_times, dtype=float))
        history = np.asarray(historical_event_times, dtype=float)

        elapsed = t[:, None] - history[None, :]
        prior_events = elapsed > 0
        decayed_excitation = np.where(
            prior_events,
            self.excitation_alpha * np.exp(-self.decay_beta * elapsed),
            0.0,
        )
        return self.background_rate_mu + np.sum(decayed_excitation, axis=1)

    def forecast_cascade_risk(self, current_time, historical_event_times):
        """Classify the current cascade risk from intensity at current_time.

        Tactical advantage: converts a raw intensity value into an
        operator-actionable risk tier without requiring manual threshold
        tuning at the point of use.
        """
        intensity = self.calc_intensity(
            current_time, historical_event_times
        )[0]
        if intensity > 5.0 * self.background_rate_mu:
            risk_tier = "CASCADE_IMMINENT"
        elif intensity > 2.0 * self.background_rate_mu:
            risk_tier = "ELEVATED"
        else:
            risk_tier = "NOMINAL"
        return {"intensity": intensity, "risk_tier": risk_tier}
