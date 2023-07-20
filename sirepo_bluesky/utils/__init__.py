import numpy as np

sigma_to_fwhm = 2 * np.sqrt(2 * np.log(2))


def get_beam_stats(image, x_extent, y_extent):
    n_y, n_x = image.shape
    image_sum = image.sum()

    if image.sum() > 0:
        X, Y = np.meshgrid(np.linspace(*x_extent, n_x), np.linspace(*y_extent, n_y))

        mean_x = np.sum(X * image) / image_sum
        mean_y = np.sum(Y * image) / image_sum

        sigma_x = np.sqrt(np.sum((X - mean_x) ** 2 * image) / image_sum)
        sigma_y = np.sqrt(np.sum((Y - mean_y) ** 2 * image) / image_sum)

    else:
        mean_x, mean_y, sigma_x, sigma_y = np.nan, np.nan, np.nan, np.nan

    return {
        "shape": (n_y, n_x),
        "flux": image_sum,
        "mean": image.mean(),
        "x": mean_x,
        "y": mean_y,
        "fwhm_x": sigma_to_fwhm * sigma_x,
        "fwhm_y": sigma_to_fwhm * sigma_y,
    }
