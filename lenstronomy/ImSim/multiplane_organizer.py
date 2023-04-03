__author__ = 'ajshajib'

import numpy as np

__all__ = ['MultiPlaneOrganizer']


class MultiPlaneOrganizer(object):
    """
    This class organizes the lens and source planes in multi-lens plane and
    multi-source plane setting.
    """
    def __init__(self, lens_redshift_list,
                 source_redshift_list,
                 sorted_lens_redshift_index,
                 sorted_source_redshift_index,
                 z_lens_convention,
                 z_source_convention, cosmo):
        """

        """
        self._lens_redshift_list = lens_redshift_list
        self._source_redshift_list = source_redshift_list

        self._sorted_lens_redshift_index = sorted_lens_redshift_index
        self._sorted_source_redshift_index = sorted_source_redshift_index

        self._sorted_joint_unique_redshift_list = sorted(list(set(
            list(lens_redshift_list) + list(source_redshift_list)
        )))

        self._num_lens_planes = len(self._sorted_joint_unique_redshift_list) \
                                    - 1 # not including the last source plane
        # self._sorted_unique_lens_redshifts = sorted(list(set(
        #     lens_redshift_list)))

        self.a_coeffs_fiducial = []
        self.b_coeffs_fiducial = []
        self._D_z_list_fiducial = []
        self._D_is_list_fiducial = [] # distance between lens planes and the last (source) plane
        self._cosmo_bkg = cosmo

        D_s = self._cosmo_bkg.d_xy(0, z_source_convention)
        if z_lens_convention != np.min(lens_redshift_list):
            raise ValueError("z_lens_convention needs to be the first lens "
                             "plane!")
        if z_source_convention != np.max(source_redshift_list):
            raise ValueError("z_source_convention needs to be the last source "
                             "plane!")
        self.z_lens_convention = z_lens_convention
        self.z_source_convention = z_source_convention

        self.D_dt_eff_fiducial = (1 + z_lens_convention) * D_s \
                                 * self._cosmo_bkg.d_xy(0, z_lens_convention) \
                                 / self._cosmo_bkg.d_xy(z_lens_convention,
                                                        z_source_convention)

        self._D_is_list_fiducial.append(self._cosmo_bkg.d_xy(0,
                                        self.z_source_convention))

        for i in range(len(self._sorted_joint_unique_redshift_list) - 1):
            z_i = self._sorted_joint_unique_redshift_list[i]
            z_ip1 = self._sorted_joint_unique_redshift_list[i + 1]

            self._D_z_list_fiducial.append(self._cosmo_bkg.d_xy(0, z_i))
            self._D_is_list_fiducial.append(self._cosmo_bkg.d_xy(z_i,
                                            self.z_source_convention))

            self.a_coeffs_fiducial.append(
                self._cosmo_bkg.d_xy(0, z_i) *
                self._cosmo_bkg.d_xy(0, z_ip1) /
                self._cosmo_bkg.d_xy(z_i, z_ip1) / self.D_dt_eff_fiducial
            )
            self.b_coeffs_fiducial.append(
                self._cosmo_bkg.d_xy(0, z_i) *
                D_s /
                self._cosmo_bkg.d_xy(z_i, z_source_convention) /
                self.D_dt_eff_fiducial
            )

        self._D_z_list_fiducial.append(self._cosmo_bkg.d_xy(0,
                                            self.z_source_convention))

    def _extract_a_b_factors(self, kwargs_special):
        """

        """
        a_factors = []
        b_factors = [1.]

        for i in range(1, self._num_lens_planes+1):
            a_factors.append(
                kwargs_special['a_{}'.format(i)]
            )
        for i in range(2, self._num_lens_planes):
            b_factors.append(
                kwargs_special['b_{}'.format(i)]
            )
        b_factors.append(a_factors[-1])

        return a_factors, b_factors

    def update_lens_T_lists(self, lens_model, kwargs_special):
        """

        """
        T_z_list, T_ij_list = self._get_lens_T_lists(kwargs_special)
        T_ij_start, T_ij_stop = self._transverse_distance_start_stop(0,
                                lens_model.lens_model.z_source,
                                kwargs_special, include_z_start=False)
        lens_model.lens_model.multi_plane_base.T_z_list = T_z_list
        lens_model.lens_model.multi_plane_base.T_ij_list = T_ij_list
        lens_model.lens_model.T_ij_start = T_ij_start
        lens_model.lens_model._T_ij_stop = T_ij_stop

    def update_source_mapping_T_lists(self, source_mapping_class,
                                      kwargs_special):
        """

        """
        T_ij_start_list, T_ij_end_list = self._get_source_T_start_end_lists(
            kwargs_special)
        source_mapping_class.T_ij_start_list = T_ij_start_list
        source_mapping_class.T_ij_end_list = T_ij_end_list

    def _get_element_index(self, arr, element):
        """

        """
        return int(np.where(np.array(arr) == element)[0][0])

    def _get_lens_T_lists(self, kwargs_special):
        """

        """
        T_ij_list = []
        T_z_list = []
        z_before = 0

        for idex in self._sorted_lens_redshift_index:
            z_lens = self._lens_redshift_list[idex]
            if z_before == z_lens:
                delta_T = 0
            else:
                #T_z = self._cosmo_bkg.T_xy(0, z_lens)
                # delta_T = self._cosmo_bkg.T_xy(z_before, z_lens)
                T_z = self._get_D_i(z_lens, kwargs_special) * (1 + z_lens)
                delta_T = self._get_D_ij(z_before, z_lens, kwargs_special) * (1 + z_lens)

            T_ij_list.append(delta_T)
            T_z_list.append(T_z)
            z_before = z_lens

        return T_z_list, T_ij_list

    def _get_D_ij(self, z_i, z_j, kwargs_special):
        """

        """
        if z_i == 0:
            return self._get_D_i(z_j, kwargs_special)
        elif z_i == z_j:
            return 0.
        elif z_j == self._sorted_joint_unique_redshift_list[-1]:
            ab_fiducial_index = self._get_element_index(
                self._sorted_joint_unique_redshift_list, z_i)
            return self._D_is_list_fiducial[ab_fiducial_index+1]

        a_factors, b_factors = self._extract_a_b_factors(kwargs_special)
        ab_fiducial_index = self._get_element_index(
            self._sorted_joint_unique_redshift_list, z_j)

        b_j = b_factors[ab_fiducial_index] * \
              self.b_coeffs_fiducial[ab_fiducial_index]
        D_j = b_j * self._D_is_list_fiducial[ab_fiducial_index + 1] * \
              self.D_dt_eff_fiducial / self._D_is_list_fiducial[0]

        if ab_fiducial_index == 0:
            raise ValueError('The code should not come here!')
            # return D_j
        else:
            ab_fiducial_index_m1 = self._get_element_index(
                self._sorted_joint_unique_redshift_list, z_i)
            assert ab_fiducial_index_m1 == ab_fiducial_index - 1

            a_j = a_factors[ab_fiducial_index] * \
                  self.a_coeffs_fiducial[ab_fiducial_index]
            a_i = a_factors[ab_fiducial_index - 1] * \
                    self.a_coeffs_fiducial[ab_fiducial_index - 1]

            b_i = b_factors[ab_fiducial_index - 1] * \
                    self.b_coeffs_fiducial[ab_fiducial_index - 1]
            D_i = b_i * self._D_is_list_fiducial[ab_fiducial_index] \
                    * self.D_dt_eff_fiducial / self._D_is_list_fiducial[0]

            D_ij = D_j * D_i / a_i / self.D_dt_eff_fiducial

            return D_ij

    def _get_D_i(self, z_i, kwargs_special):
        """

        """
        if z_i == 0.:
            return 0.
        elif z_i == self._sorted_joint_unique_redshift_list[-1]:
            return self._D_is_list_fiducial[0]

        a_factors, b_factors = self._extract_a_b_factors(kwargs_special)

        ab_fiducial_index = self._get_element_index(
            self._sorted_joint_unique_redshift_list, z_i)

        b_i = b_factors[ab_fiducial_index] * \
              self.b_coeffs_fiducial[ab_fiducial_index]
        D_i = b_i * self._D_is_list_fiducial[
            ab_fiducial_index + 1] * \
              self.D_dt_eff_fiducial / \
              self._D_is_list_fiducial[0]

        return D_i

    def _transverse_distance_start_stop(self, z_start, z_stop, kwargs_special,
                                       include_z_start=False):
        """
        computes the transverse distance (T_ij) that is required by the ray-tracing between the starting redshift and
        the first deflector afterwards and the last deflector before the end of the ray-tracing.

        :param z_start: redshift of the start of the ray-tracing
        :param z_stop: stop of ray-tracing
        :param include_z_start: boolean, if True includes the computation of the starting position if the first
         deflector is at z_start
        :return: T_ij_start, T_ij_end
        """
        z_lens_last = z_start
        first_deflector = True
        T_ij_start = None
        for i, idex in enumerate(self._sorted_lens_redshift_index):
            z_lens = self._lens_redshift_list[idex]
            if self._start_condition(include_z_start, z_lens, z_start) and z_lens <= z_stop:
                if first_deflector is True:
                    T_ij_start = self._get_D_ij(z_start, z_lens,
                                                kwargs_special) * (1 + z_lens)
                    first_deflector = False
                z_lens_last = z_lens
        T_ij_end = self._get_D_ij(z_lens_last, z_stop, kwargs_special)\
                                                        * (1 + z_stop)
        return T_ij_start, T_ij_end

    def _get_source_T_start_end_lists(self, kwargs_special,
                                     include_z_start=False):
        """

        """
        #self._sorted_source_redshift_index
        z_start = 0
        T_ij_start_list = []
        T_ij_end_list = []

        for i, index_source in enumerate(self._sorted_source_redshift_index):
            z_stop = self._source_redshift_list[index_source]
            T_ij_start, T_ij_end = self._transverse_distance_start_stop(
                z_start, z_stop, kwargs_special,
                include_z_start=False)
            T_ij_start_list.append(T_ij_start)
            T_ij_end_list.append(T_ij_end)
            z_start = z_stop

        return T_ij_start_list, T_ij_end_list

    @staticmethod
    def _start_condition(inclusive, z_lens, z_start):
        """

        :param inclusive: boolean, if True selects z_lens including z_start, else only selects z_lens > z_start
        :param z_lens: deflector redshift
        :param z_start: starting redshift (lowest redshift)
        :return: boolean of condition
        """

        if inclusive:
            return z_lens >= z_start
        else:
            return z_lens > z_start