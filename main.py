import sys

from lib import *
import lib
import os
import pathlib
import calibrate

LOGFILE_PATH = "cyberzoo_tests_the_second/config_a"
LOGFILES_ROOT = "input"
SAVE_FOR_PUBLICATION = False

j, _, __ = calibrate.calibrateFlywheel("cyberzoo_tests_the_second",
                                dirlist=["device", "calibration"],
                                GROUNDTRUTH_PATH="calibration",
                                new_motor=True)

for (dirpath, dirnames, filenames) in os.walk(os.path.join(LOGFILES_ROOT, LOGFILE_PATH)):
    for f in filenames:
        if ".py" in f:
            continue
        print(f)
        df, omegas, accelerations, times, flywheel_omegas \
            = importDatafile(os.path.join(LOGFILES_ROOT, LOGFILE_PATH, f))

        # Prepare discrete filter coefficients
        filter_cutoff = 100
        dt = (times[-1] - times[0])/len(times)
        lib.filter_coefs = recomputeFilterCoefficients(filter_cutoff, dt)

        # Apply filter to data
        filtered_omegas = filterVectorSignal(omegas)
        filtered_flywheel_omegas = filterVectorSignal(flywheel_omegas)
        filtered_accelerations = filterVectorSignal(accelerations)

        # Numerically differentiate filtered signals
        jerks = differentiateVectorSignal(filtered_accelerations, dt)
        omega_dots = differentiateVectorSignal(filtered_omegas, dt)
        flywheel_omega_dots = differentiateVectorSignal(filtered_flywheel_omegas, dt)

        filtered_omegas = delaySavGolFilterVectorSignal(filtered_omegas)
        filtered_flywheel_omegas = delaySavGolFilterVectorSignal(filtered_flywheel_omegas)

        # Find lengths of filtered values
        absolute_accelerations = np.sqrt(accelerations[:,0] ** 2 +
                                         accelerations[:,1] ** 2 +
                                         accelerations[:,2] ** 2)
        absolute_omegas = np.sqrt(omegas[:,0] ** 2 +
                                  omegas[:,1] ** 2 +
                                  omegas[:,2] ** 2)
        absolute_jerks = np.sqrt(jerks[:,0] ** 2 +
                                 jerks[:,1] ** 2 +
                                 jerks[:,2] ** 2)

        # # Initialise plot
        fig, (ax1, ax2) = plt.subplots(2, 1, sharex="col", gridspec_kw={'height_ratios': [2, 1]})
        # timePlotVector(times, omegas, ax=ax1, label="Measured", ylabel=r"${\omega}$ (rad/s)")
        # timePlotVector(times, filtered_omegas, ax=ax1, label="Filtered", alpha=0.5)
        # timePlotVector(times, omega_dots, ax=ax1, label="Angular acceleration", linestyle="dashed", alpha=0.7)
        # timePlotVector(times, flywheel_omega_dots, ax=ax2, label="Flywheel angular acceleration", linestyle="dashed", alpha=0.7)

        timePlotVector(times, accelerations, ax=ax1, label="Measured", alpha=0.2)
        timePlotVector(times, filtered_accelerations, ax=ax1, label="Filtered")

        timePlotVector(times, flywheel_omegas, ax=ax2, label="Measured", ylabel=r"${\omega}_f$ (rad/s)")
        timePlotVector(times, filtered_flywheel_omegas, ax=ax2, label="Filtered", ylabel=r"${\omega}_f$ (rad/s)", alpha=0.5)
        ax2.invert_yaxis()

        starts, ends = detectThrow(times, absolute_omegas, absolute_accelerations, absolute_jerks, flywheel_omegas)

        if len(starts) == 0:
             print("No throws detected")
             continue
             # plt.show()
             # sys.exit()

        # Set flywheel inertia
        lib.Jflywheel = j # kg*m^2

        throw_offset = 300

        # Compute inertia tensor with filtered data
        I, residuals = computeI(filtered_omegas[starts[0]+throw_offset:],
                     omega_dots[starts[0]+throw_offset:],
                     filtered_flywheel_omegas[starts[0]+throw_offset:],
                     flywheel_omega_dots[starts[0]+throw_offset:])
        x, resx = computeX(filtered_omegas[starts[0]+throw_offset:],
                     omega_dots[starts[0]+throw_offset:],
                     filtered_accelerations[starts[0]+throw_offset:])
        print(I)

        sys.path.append(os.path.join(LOGFILES_ROOT, LOGFILE_PATH))
        import groundtruth

        computeError(I, groundtruth.trueInertia)

        # simulation_omegas = simulateThrow(I,
        #                                   times[starts[0]+throw_offset:],
        #                                   filtered_omegas[starts[0]+throw_offset],
        #                                   filtered_flywheel_omegas[starts[0]+throw_offset:],
        #                                   flywheel_omega_dots[starts[0]+throw_offset:])
        # timePlotVector(times[starts[0]+throw_offset+1:], simulation_omegas, label="Simulated", ax=ax1, linestyle="dashed", alpha=0.8)

        ax2.get_legend().remove()

        for s in starts:
            ax1.axvline([times[s + throw_offset] * 1e3], linestyle="dashed", color="gray")
        for e in ends:
            ax1.axvline([times[e + throw_offset] * 1e3], linestyle="dotted", color="darkgray")

        ax1.set_xlim([times[starts[0]] * 1e3, times[-1] * 1e3])

        ax1.grid()
        ax2.grid()

        filename = os.path.splitext(os.path.join("output", LOGFILE_PATH, f))[0] + "-simulation.pdf"
        pathlib.Path(os.path.dirname(filename)).mkdir(parents=True, exist_ok=True)

        plt.savefig(filename, transparent=True, dpi=300, format="pdf", bbox_inches="tight")
        if SAVE_FOR_PUBLICATION:
            filename = os.path.splitext(os.path.join("output", LOGFILE_PATH, f))[0] + "-simulation_publication.pdf"
            fig.set_size_inches(10, 2.5)
            plt.savefig(filename, transparent=True, dpi=300, format="pdf", bbox_inches="tight")
        else:
            # formatTicks(100, 20)
            plt.tight_layout()
            plt.show()
    break