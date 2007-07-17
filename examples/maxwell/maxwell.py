# Hedge - the Hybrid'n'Easy DG Environment
# Copyright (C) 2007 Andreas Kloeckner
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.




from __future__ import division
import pylinear.array as num
import pylinear.computation as comp




def main():
    from hedge.element import TriangularElement, TetrahedralElement
    from hedge.timestep import RK4TimeStepper
    from hedge.mesh import make_ball_mesh, make_cylinder_mesh, make_box_mesh
    from hedge.discretization import \
            Discretization, \
            bind_flux, \
            bind_nabla, \
            bind_mass_matrix, \
            bind_inverse_mass_matrix, \
            pair_with_boundary
    from hedge.visualization import SiloVisualizer
    from hedge.silo import SiloFile
    from hedge.silo import DB_VARTYPE_VECTOR
    from hedge.tools import dot, cross, EOCRecorder
    from math import sqrt, pi
    from analytic_solutions import \
            check_time_harmonic_solution, \
            RealPartAdapter, \
            SplitComplexAdapter, \
            CartesianAdapter, \
            CylindricalCavityMode, \
            RectangularCavityMode
    from hedge.operators import MaxwellOperator

    epsilon0 = 8.8541878176e-12 # C**2 / (N m**2)
    mu0 = 4*pi*1e-7 # N/A**2.
    epsilon = 1*epsilon0
    mu = 1*mu0

    eoc_rec = EOCRecorder()

    cylindrical = False

    if cylindrical:
        R = 1
        d = 2
        mode = CylindricalCavityMode(m=1, n=1, p=1,
                radius=R, height=d, 
                epsilon=epsilon, mu=mu)
        r_sol = CartesianAdapter(RealPartAdapter(mode))
        c_sol = SplitComplexAdapter(CartesianAdapter(mode))
        mesh = make_cylinder_mesh(radius=R, height=d, max_volume=0.01)
    else:
        mode = RectangularCavityMode(epsilon, mu, (3,2,1))
        r_sol = RealPartAdapter(mode)
        c_sol = SplitComplexAdapter(mode)
        mesh = make_box_mesh(max_volume=0.01)

    #for order in [1,2,3,4,5,6]:
    for order in [3]:
        print "---------------------------------------------"
        print "order %d" % order
        print "---------------------------------------------"
        discr = Discretization(mesh, TetrahedralElement(order))
        vis = SiloVisualizer(discr)

        print "%d elements" % len(discr.mesh.elements)

        dt = discr.dt_factor(1/sqrt(mu*epsilon))
        final_time = dt*60
        nsteps = int(final_time/dt)+1
        dt = final_time/nsteps

        print "dt", dt
        print "nsteps", nsteps

        mass = bind_mass_matrix(discr)

        def l2_norm(field):
            return sqrt(dot(field, mass*field))

        #check_time_harmonic_solution(discr, mode, c_sol)
        #continue

        mode.set_time(0)
        fields = discr.interpolate_volume_function(r_sol)
        op = MaxwellOperator(discr, epsilon, mu, upwind_alpha=1)

        stepper = RK4TimeStepper()
        from time import time
        last_tstep = time()
        t = 0
        for step in range(nsteps):
            print "timestep %d, t=%f l2[e]=%g l2[h]=%g secs=%f" % (
                    step, t, l2_norm(fields[0:3]), l2_norm(fields[3:6]),
                    time()-last_tstep)
            last_tstep = time()

            silo = SiloFile("em-%04d.silo" % step)
            vis.add_to_silo(silo,
                    vectors=[("e", fields[0:3]), 
                        ("h", fields[3:6]), ],
                    expressions=[
                        ],
                    write_coarse_mesh=True,
                    time=t, step=step
                    )

            fields = stepper(fields, t, dt, op.rhs)
            t += dt

        mode.set_time(t)
        true_fields = discr.interpolate_volume_function(r_sol)
        eoc_rec.add_data_point(order, l2_norm(fields-true_fields))

        print
        print eoc_rec.pretty_print("P.Deg.", "L2 Error")

if __name__ == "__main__":
    import cProfile as profile
    #profile.run("main()", "wave2d.prof")
    main()