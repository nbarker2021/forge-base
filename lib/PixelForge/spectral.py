"""
PixelForge Spectral — generic band-limited FFT decomposition: a series ->
(direct, spectral reconstruction, residual).

De-marketized reimplementation of historical_pastworks/wave_centroid_v2.py's
decompose_band — that tool applies exactly this analysis (detrend, Hann
window, FFT, band-pass mask, reconstruct from the top-N in-band components,
residual = direct - spectral) to a price series to get a "spectral wave"
and a residual signal. The math has nothing to do with prices; this module
is the same decomposition with the domain-specific parts (log-price,
trading-day band names) removed, so it applies to any real-valued series —
in this build, SplatForge.gluon_blob.sweep_spectral_residue runs it on the
correction_firing_fraction series a multi-frame sweep already produces.

Honesty note: this is the first PixelForge module that needs numpy (FFT in
pure Python is impractical at any useful resolution). SplatForge.tiling
already depends on numpy, so this is not a new project dependency — it is
the first time PixelForge itself uses one, said plainly rather than left
for someone to discover.
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence

import numpy as np


def decompose_band(series: Sequence[float], min_period: float = 3.0,
                    max_period: float = None, top_n: int = 3) -> Dict[str, Any]:
    """Band-limited FFT decomposition of `series`.

    direct    = series, linearly detrended.
    spectral  = direct, reconstructed from only the top_n highest-amplitude
                frequency components whose period falls in
                [min_period, max_period] (defaults to the full Nyquist
                range when max_period is None).
    residual  = direct - spectral, by construction.

    Falls back to the full valid-period range (period in [2, n]) if no
    frequency component's period lands in the requested band — the same
    fallback wave_centroid_v2 uses, so a too-narrow band on a short series
    degrades gracefully instead of returning an all-zero spectral wave.
    """
    values = np.asarray(series, dtype=float)
    n = len(values)
    if n < 2:
        raise ValueError("decompose_band requires at least 2 samples")
    if max_period is None:
        max_period = float(n)

    idx = np.arange(n)
    trend = np.polyfit(idx, values, 1)
    trend_line = np.polyval(trend, idx)
    direct = values - trend_line

    window = np.hanning(n) if n > 1 else np.ones(n)
    fft_vals = np.fft.rfft(direct * window)
    freqs = np.fft.rfftfreq(n)
    amplitudes = np.abs(fft_vals)
    nonzero = freqs > 0
    periods = np.full_like(freqs, np.inf)
    periods[nonzero] = 1.0 / freqs[nonzero]

    band_mask = (periods >= min_period) & (periods <= max_period)
    band_indices = np.where(band_mask)[0]
    if len(band_indices) == 0:
        valid_mask = (periods >= 2) & (periods <= n)
        band_indices = np.where(valid_mask)[0]

    sorted_by_amp = band_indices[np.argsort(amplitudes[band_indices])[::-1]]
    top_indices = sorted_by_amp[:top_n]

    fft_filtered = np.zeros_like(fft_vals)
    for i in top_indices:
        fft_filtered[i] = fft_vals[i]
    spectral = np.fft.irfft(fft_filtered, n=n)

    residual = direct - spectral
    dom_period = float(periods[top_indices[0]]) if len(top_indices) else (min_period + max_period) / 2
    cycles: List[Dict[str, float]] = [
        {"period": float(periods[i]), "amplitude": float(amplitudes[i])}
        for i in top_indices
    ]

    return {
        "direct": [round(float(v), 8) for v in direct],
        "spectral": [round(float(v), 8) for v in spectral],
        "residual": [round(float(v), 8) for v in residual],
        "dom_period": round(dom_period, 6),
        "cycles": cycles,
        "n": n,
        "min_period": min_period,
        "max_period": max_period,
    }
