import numpy as np


def get_beam_stats(image, x_extent, y_extent):
    n_y, n_x = image.shape

    if image.sum() > 0:
        X, Y = np.meshgrid(np.linspace(*x_extent, n_x), np.linspace(*y_extent, n_y))

        mean_x = np.sum(X * image) / np.sum(image)
        mean_y = np.sum(Y * image) / np.sum(image)

        sigma_x = np.sqrt(np.sum((X - mean_x) ** 2 * image) / np.sum(image))
        sigma_y = np.sqrt(np.sum((Y - mean_y) ** 2 * image) / np.sum(image))

    else:
        mean_x, mean_y, sigma_x, sigma_y = np.nan, np.nan, np.nan, np.nan

    return {
        "shape": (n_y, n_x),
        "flux": image.sum(),
        "mean": image.mean(),
        "x": mean_x,
        "y": mean_y,
        "fwhm_x": 2 * np.sqrt(2 * np.log(2)) * sigma_x,
        "fwhm_y": 2 * np.sqrt(2 * np.log(2)) * sigma_y,
    }
