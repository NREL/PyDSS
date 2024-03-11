from typing import Union, Annotated

from pydantic import BaseModel, Field, model_validator

from PyDSS.pyControllers.enumerations import CategoryI, CategoryII, CategoryIII, PvStandard, VoltageCalcModes, RideThroughCategory, PermissiveOperation, MayTripOperation, MultipleDisturbances



class BaseControllerModel(BaseModel):
    ...
    
    
class PvVoltageRideThruModel(BaseControllerModel):
    """Data model for the PV voltage ride through controller"""
    
    kva : Annotated[
        float,
        Field(4.0, ge=0.0, description="kVA capacity of the inverter (AC-side)."),
    ] 
    max_kw: Annotated[
        float,
        Field(4.0, ge=0.0, description="kW capacity of the PV system (DC-side)."),
    ] 
    voltage_calc_mode: Annotated[
        VoltageCalcModes,
        Field(VoltageCalcModes.MAX, description="Voltage values used to calculate Var support from the inverter (Maximum or Average)."),
    ] 
    follow_standard: Annotated[
        PvStandard,
        Field(PvStandard.IEEE_1547_2018, description="IEEE standard the inverter is following."),
    ] 
    ride_through_category : Annotated[
        RideThroughCategory,
        Field(RideThroughCategory.CATEGORY_I, description="PV ride-through category fot the inverter (see IEEE 1547-2018 std for more information)."),
    ] 
    ov_2_pu: Annotated[
        float,
        Field(CategoryI.OV2_PU.value, description="Upper bound for the over-voltage region."),
    ] 
    ov_2_ct_sec: Annotated[
        float,
        Field(CategoryI.OV2_CT_SEC.value, description="Trip duration setting if the upper bound of the over-voltage region is violated."),
    ] 
    ov_1_pu: Annotated[
        float,
        Field(CategoryI.OV1_PU.value, description="Lower bound for the over-voltage region."),
    ] 
    ov_1_ct_sec: Annotated[
        float,
        Field(CategoryI.OV1_CT_SEC.value, description="Trip duration setting if the lower bound of the over-voltage region is violated."),
    ] 
    uv_1_pu: Annotated[
        float,
        Field(CategoryI.UV1_PU.value, description="Upper bound for the under-voltage region."),
    ] 
    uv_1_ct_sec: Annotated[
        float,
        Field(CategoryI.UV1_CT_SEC.value, description="Trip duration setting if the upper bound of the under-voltage region is violated."),
    ] 
    uv_2_pu:  Annotated[
        float,
        Field(CategoryI.UV2_PU.value, description="Lower bound for the under-voltage region."),
    ]   
    uv_2_ct_sec: Annotated[
        float,
        Field(CategoryI.UV2_CT_SEC.value, description="Trip duration setting if the upper bound of the under-voltage region is violated."),
    ] 
    reconnect_deadtime_sec : Annotated[
        float,
        Field(3000.0, ge=0.0, description=""),
    ] 
    reconnect_pmax_time_sec : Annotated[
        float,
        Field(300.0, ge=0.0, description="Reconnect after a trip event. PV system will connect back once this time has elapsed and the system voltage is within bounds."),
    ] 
    permissive_operation: Annotated[
        PermissiveOperation,
        Field(PermissiveOperation.CURRENT_LIMITED, description="Defines behavior of the system within the 'permissive operation' region. (see IEEE 1547-2018 std for more information)."),
    ] 
    may_trip_operation: Annotated[
        MayTripOperation,
        Field(MayTripOperation.TRIP, description="Defines behavior of the system within the 'may trip' region. (see IEEE 1547-2018 std for more information)."),
    ] 
    multiple_disturdances: Annotated[
        MultipleDisturbances,
        Field(MultipleDisturbances.TRIP, description="Defines behavior of the system after multiple disturbances. (see IEEE 1547-2018 std for more information)."),
    ] 

    @model_validator(mode='after')
    def update_settings(self) -> 'PvVoltageRideThruModel':
        cat1 = self.ride_through_category == RideThroughCategory.CATEGORY_I
        cat2 = self.ride_through_category == RideThroughCategory.CATEGORY_II
          
        self.ov_2_pu = CategoryI.OV2_PU.value if cat1 else CategoryII.OV2_PU.value if cat2 else CategoryIII.OV2_PU.value
        self.ov_1_pu = CategoryI.OV1_PU.value if cat1 else CategoryII.OV1_PU.value if cat2 else CategoryIII.OV1_PU.value
        self.uv_2_pu = CategoryI.UV2_PU.value if cat1 else CategoryII.UV2_PU.value if cat2 else CategoryIII.UV2_PU.value
        self.uv_1_pu = CategoryI.UV1_PU.value if cat1 else CategoryII.UV1_PU.value if cat2 else CategoryIII.UV1_PU.value     
        self.ov_2_ct_sec = CategoryI.OV2_CT_SEC.value if cat1 else CategoryII.OV2_CT_SEC.value if cat2 else CategoryIII.OV2_CT_SEC.value
        self.ov_1_ct_sec = CategoryI.OV1_CT_SEC.value if cat1 else CategoryII.OV1_CT_SEC.value if cat2 else CategoryIII.OV1_CT_SEC.value
        self.uv_2_ct_sec = CategoryI.UV2_CT_SEC.value if cat1 else CategoryII.UV2_CT_SEC.value if cat2 else CategoryIII.UV2_CT_SEC.value
        self.uv_1_ct_sec = CategoryI.UV1_CT_SEC.value if cat1 else CategoryII.UV1_CT_SEC.value if cat2 else CategoryIII.UV1_CT_SEC.value
        
        return self



class PvSmartController(BaseControllerModel):
    kvar_limit: Annotated[
        float,
        Field(1.76, ge=0.0, description="kVar capacity of the PV system."),
    ] 
    pct_p_cutin: Annotated[
        float,
        Field(10.0, ge=0.0, le=100.0, description="Percentage of kVA rating of inverter. When the inverter is OFF, the power from the system must be greater than this for the inverter to turn on"),
    ] 
    pct_p_cutout: Annotated[
        float,
        Field(10.0, ge=0.0, le=100.0, description="Percentage of kVA rating of inverter. When the inverter is ON, the inverter turns OFF when the power from the array drops below this value."),
    ] 
    enable_pf_limit: Annotated[
        bool,
        Field(False, description="Enable flag to apply power factor limits on the inverter output"),
    ] 
    pf_min: Annotated[
        float,
        Field(0.95, ge=0.0, le=1.0, description="Minimum allowable powerfactor for the system. 'enable_pf_limit' should be enable for the constraint to be implemented."),
    ] 