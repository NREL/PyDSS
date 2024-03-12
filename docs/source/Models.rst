Data models
+++++++++++

Simulation input models
************************

.. autopydantic_model:: PyDSS.simulation_input_models.SnapshotTimePointSelectionConfigModel

.. autopydantic_model:: PyDSS.simulation_input_models.ScenarioPostProcessModel

.. autopydantic_model:: PyDSS.simulation_input_models.ScenarioModel

.. autopydantic_model:: PyDSS.simulation_input_models.ProjectModel

.. autopydantic_model:: PyDSS.simulation_input_models.ExportsModel

.. autopydantic_model:: PyDSS.simulation_input_models.FrequencyModel

.. autopydantic_model:: PyDSS.simulation_input_models.HelicsModel

.. autopydantic_model:: PyDSS.simulation_input_models.LoggingModel

.. autopydantic_model:: PyDSS.simulation_input_models.MonteCarloModel

.. autopydantic_model:: PyDSS.simulation_input_models.ProfilesModel

.. autopydantic_model:: PyDSS.simulation_input_models.ReportBaseModel

.. autopydantic_model:: PyDSS.simulation_input_models.CapacitorStateChangeCountReportModel

.. autopydantic_model:: PyDSS.simulation_input_models.FeederLossesReportModel

.. autopydantic_model:: PyDSS.simulation_input_models.FeederLossesReportModel

.. autopydantic_model:: PyDSS.simulation_input_models.PvClippingReportModel

.. autopydantic_model:: PyDSS.simulation_input_models.PvCurtailmentReportModel

.. autopydantic_model:: PyDSS.simulation_input_models.RegControlTapNumberChangeCountsReportModel

.. autopydantic_model:: PyDSS.simulation_input_models.ThermalMetricsReportModel

.. autopydantic_model:: PyDSS.simulation_input_models.VoltageMetricsReportModel

.. autopydantic_model:: PyDSS.simulation_input_models.ReportsModel

.. autopydantic_model:: PyDSS.simulation_input_models.SimulationSettingsModel

Scenario setup models
************************

.. autopydantic_model:: PyDSS.controllers.ControllerBaseModel

.. autopydantic_model:: PyDSS.controllers.PvControllerModel


Thermal metrics models
**********************

.. autopydantic_model:: PyDSS.thermal_metrics.ThermalMetricsBaseModel

.. autopydantic_model:: PyDSS.thermal_metrics.ThermalMetricsModel

.. autopydantic_model:: PyDSS.thermal_metrics.ThermalMetricsSummaryModel

.. autopydantic_model:: PyDSS.thermal_metrics.SimulationThermalMetricsModel

Voltage metrics models
**********************

.. autopydantic_model:: PyDSS.node_voltage_metrics.VoltageMetricsBaseModel

.. autopydantic_model:: PyDSS.node_voltage_metrics.VoltageMetric1

.. autopydantic_model:: PyDSS.node_voltage_metrics.VoltageMetric2

.. autopydantic_model:: PyDSS.node_voltage_metrics.VoltageMetric3

.. autopydantic_model:: PyDSS.node_voltage_metrics.VoltageMetric4

.. autopydantic_model:: PyDSS.node_voltage_metrics.VoltageMetric5

.. autopydantic_model:: PyDSS.node_voltage_metrics.VoltageMetric5

.. autopydantic_model:: PyDSS.node_voltage_metrics.VoltageMetricsSummaryModel

.. autopydantic_model:: PyDSS.node_voltage_metrics.VoltageMetricsModel

.. autopydantic_model:: PyDSS.node_voltage_metrics.VoltageMetricsByBusTypeModel

.. autopydantic_model:: PyDSS.node_voltage_metrics.SimulationVoltageMetricsModel


Feeder metrics models
**********************

.. autopydantic_model:: PyDSS.reports.feeder_losses.FeederLossesMetricsModel

.. autopydantic_model:: PyDSS.reports.feeder_losses.SimulationFeederLossesMetricsModel


HELICS interface models
************************

.. autopydantic_model:: PyDSS.helics_interface.Subscription

.. autopydantic_model:: PyDSS.helics_interface.Publication

.. autopydantic_model:: PyDSS.helics_interface.Subscriptions

.. autopydantic_model:: PyDSS.helics_interface.Publications