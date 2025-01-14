# -*- coding: utf-8 -*-
# numpydoc ignore=GL08

from __future__ import annotations

from typing import NamedTuple

import jax.numpy as jnp
import pyrenew.arrayutils as au
from jax.typing import ArrayLike
from pyrenew.metaclass import Model, RandomVariable, _assert_sample_and_rtype
from pyrenew.model.rtinfectionsrenewalmodel import RtInfectionsRenewalModel


class HospModelSample(NamedTuple):
    """
    A container for holding the output from `model.HospitalAdmissionsModel.sample()`.

    Attributes
    ----------
    Rt : float | None, optional
        The reproduction number over time. Defaults to None.
    latent_infections : ArrayLike | None, optional
        The estimated number of new infections over time. Defaults to None.
    infection_hosp_rate : float | None, optional
        The infected hospitalization rate. Defaults to None.
    latent_hosp_admissions : ArrayLike | None, optional
        The estimated latent hospitalizations. Defaults to None.
    observed_hosp_admissions : ArrayLike | None, optional
        The sampled or observed hospital admissions. Defaults to None.
    """

    Rt: float | None = None
    latent_infections: ArrayLike | None = None
    infection_hosp_rate: float | None = None
    latent_hosp_admissions: ArrayLike | None = None
    observed_hosp_admissions: ArrayLike | None = None

    def __repr__(self):
        return (
            f"HospModelSample(Rt={self.Rt}, "
            f"latent_infections={self.latent_infections}, "
            f"infection_hosp_rate={self.infection_hosp_rate}, "
            f"latent_hosp_admissions={self.latent_hosp_admissions}, "
            f"observed_hosp_admissions={self.observed_hosp_admissions}"
        )


class HospitalAdmissionsModel(Model):
    """
    Hospital Admissions Model (BasicRenewal + HospitalAdmissions)

    This class inherits from pyrenew.models.Model. It extends the
    basic renewal model by adding a hospital admissions module, e.g.,
    pyrenew.observations.HospitalAdmissions.
    """

    def __init__(
        self,
        latent_hosp_admissions_rv: RandomVariable,
        latent_infections_rv: RandomVariable,
        gen_int_rv: RandomVariable,
        I0_rv: RandomVariable,
        Rt_process_rv: RandomVariable,
        hosp_admission_obs_process_rv: RandomVariable,
    ) -> None:  # numpydoc ignore=PR04
        """
        Default constructor

        Parameters
        ----------
        latent_hosp_admissions_rv : RandomVariable
            Latent process for the hospital admissions.
        latent_infections_rv : RandomVariable
            The infections latent process (passed to RtInfectionsRenewalModel).
        gen_int_rv : RandomVariable
            Generation time (passed to RtInfectionsRenewalModel)
        I0_rv : RandomVariable
            Initial infections (passed to RtInfectionsRenewalModel)
        Rt_process_rv : RandomVariable
            Rt process  (passed to RtInfectionsRenewalModel).
        hosp_admission_obs_process_rv : RandomVariable, optional
            Observation process for the hospital admissions.

        Returns
        -------
        None
        """
        self.basic_renewal = RtInfectionsRenewalModel(
            gen_int_rv=gen_int_rv,
            I0_rv=I0_rv,
            latent_infections_rv=latent_infections_rv,
            infection_obs_process_rv=None,  # why is this None?
            Rt_process_rv=Rt_process_rv,
        )

        HospitalAdmissionsModel.validate(
            latent_hosp_admissions_rv, hosp_admission_obs_process_rv
        )

        self.latent_hosp_admissions_rv = latent_hosp_admissions_rv
        self.hosp_admission_obs_process_rv = hosp_admission_obs_process_rv

    @staticmethod
    def validate(
        latent_hosp_admissions_rv, hosp_admission_obs_process_rv
    ) -> None:
        """
        Verifies types and status (RV) of latent and observed hospital admissions

        Parameters
        ----------
        latent_hosp_admissions_rv : RandomVariable
            The latent process for the hospital admissions.
        hosp_admission_obs_process_rv : RandomVariable
            The observed hospital admissions.

        Returns
        -------
        None

        See Also
        --------
        _assert_sample_and_rtype : Perform type-checking and verify RV
        """
        _assert_sample_and_rtype(latent_hosp_admissions_rv, skip_if_none=False)
        _assert_sample_and_rtype(
            hosp_admission_obs_process_rv, skip_if_none=True
        )
        return None

    def sample_latent_hosp_admissions(
        self,
        latent_infections: ArrayLike,
        **kwargs,
    ) -> tuple:
        """
        Sample number of hospital admissions

        Parameters
        ----------
        infections : ArrayLike
            The predicted infections array.
        **kwargs : dict, optional
            Additional keyword arguments passed through to internal
            sample() calls, should there be any.

        Returns
        -------
        tuple

        See Also
        --------
        latent_hosp_admissions.sample : For sampling latent hospital admissions
        """

        return self.latent_hosp_admissions_rv.sample(
            latent_infections=latent_infections,
            **kwargs,
        )

    def sample_admissions_process(
        self,
        observed_hosp_admissions_mean: ArrayLike,
        data_observed_hosp_admissions: ArrayLike,
        name: str | None = None,
        **kwargs,
    ) -> tuple:
        """
        Sample number of hospital admissions

        Parameters
        ----------
        observed_hosp_admissions_mean : ArrayLike
            The mean of the predictive distribution for observed hospital admissions.
        obs : ArrayLike
            The observed hospitalization data (to fit).
        name : str, optional
            Name of the random variable. Defaults to None.
        **kwargs : dict, optional
            Additional keyword arguments passed through to internal
            obs calls, should there be any.

        Returns
        -------
        tuple
        """

        return self.hosp_admission_obs_process_rv.sample(
            mu=observed_hosp_admissions_mean,
            obs=data_observed_hosp_admissions,
            name=name,
            **kwargs,
        )

    def sample(
        self,
        n_timepoints_to_simulate: int | None = None,
        data_observed_hosp_admissions: ArrayLike | None = None,
        padding: int = 0,
        **kwargs,
    ) -> HospModelSample:
        """
        Sample from the HospitalAdmissions model

        Parameters
        ----------
        n_timepoints_to_simulate : int, optional
            Number of timepoints to sample (passed to the basic renewal model).
        data_observed_hosp_admissions : ArrayLike, optional
            The observed hospitalization data (passed to the basic renewal
            model). Defaults to None (simulation, rather than fit).
        padding : int, optional
            Number of padding timepoints to add to the beginning of the
            simulation. Defaults to 0.
        **kwargs : dict, optional
            Additional keyword arguments passed through to internal sample()
            calls, should there be any.

        Returns
        -------
        HospModelSample

        See Also
        --------
        basic_renewal.sample : For sampling the basic renewal model
        sample_latent_hosp_admissions : To sample latent hospitalization process
        sample_observed_admissions : For sampling observed hospital admissions
        """
        if (
            n_timepoints_to_simulate is None
            and data_observed_hosp_admissions is None
        ):
            raise ValueError(
                "Either n_timepoints_to_simulate or data_observed_hosp_admissions "
                "must be passed."
            )
        elif (
            n_timepoints_to_simulate is not None
            and data_observed_hosp_admissions is not None
        ):
            raise ValueError(
                "Cannot pass both n_timepoints_to_simulate and data_observed_hosp_admissions."
            )
        elif n_timepoints_to_simulate is None:
            n_timepoints = len(data_observed_hosp_admissions)
        else:
            n_timepoints = n_timepoints_to_simulate

        # Getting the initial quantities from the basic model
        basic_model = self.basic_renewal.sample(
            n_timepoints_to_simulate=n_timepoints,
            data_observed_infections=None,
            padding=padding,
            **kwargs,
        )

        # Sampling the latent hospital admissions
        (
            infection_hosp_rate,
            latent_hosp_admissions,
            *_,
        ) = self.sample_latent_hosp_admissions(
            latent_infections=basic_model.latent_infections,
            **kwargs,
        )
        i0_size = len(latent_hosp_admissions) - n_timepoints
        if self.hosp_admission_obs_process_rv is None:
            observed_hosp_admissions = None
        else:
            if data_observed_hosp_admissions is None:
                (
                    observed_hosp_admissions,
                    *_,
                ) = self.sample_admissions_process(
                    observed_hosp_admissions_mean=latent_hosp_admissions,
                    data_observed_hosp_admissions=data_observed_hosp_admissions,
                    **kwargs,
                )
            else:
                data_observed_hosp_admissions = au.pad_x_to_match_y(
                    data_observed_hosp_admissions,
                    latent_hosp_admissions,
                    jnp.nan,
                    pad_direction="start",
                )

                (
                    observed_hosp_admissions,
                    *_,
                ) = self.sample_admissions_process(
                    observed_hosp_admissions_mean=latent_hosp_admissions[
                        i0_size + padding :
                    ],
                    data_observed_hosp_admissions=data_observed_hosp_admissions[
                        i0_size + padding :
                    ],
                    **kwargs,
                )

        return HospModelSample(
            Rt=basic_model.Rt,
            latent_infections=basic_model.latent_infections,
            infection_hosp_rate=infection_hosp_rate,
            latent_hosp_admissions=latent_hosp_admissions,
            observed_hosp_admissions=observed_hosp_admissions,
        )
