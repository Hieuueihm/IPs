# Definitional proc to organize widgets for parameters.
proc init_gui { IPINST } {
  ipgui::add_param $IPINST -name "Component_Name"
  #Adding Page
  set Page_0 [ipgui::add_page $IPINST -name "Page 0"]
  ipgui::add_param $IPINST -name "SAMPLING_RATE" -parent ${Page_0}
  ipgui::add_param $IPINST -name "SYSTEM_FREQUENCY" -parent ${Page_0}


}

proc update_PARAM_VALUE.SAMPLING_RATE { PARAM_VALUE.SAMPLING_RATE } {
	# Procedure called to update SAMPLING_RATE when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.SAMPLING_RATE { PARAM_VALUE.SAMPLING_RATE } {
	# Procedure called to validate SAMPLING_RATE
	return true
}

proc update_PARAM_VALUE.SYSTEM_FREQUENCY { PARAM_VALUE.SYSTEM_FREQUENCY } {
	# Procedure called to update SYSTEM_FREQUENCY when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.SYSTEM_FREQUENCY { PARAM_VALUE.SYSTEM_FREQUENCY } {
	# Procedure called to validate SYSTEM_FREQUENCY
	return true
}


proc update_MODELPARAM_VALUE.SYSTEM_FREQUENCY { MODELPARAM_VALUE.SYSTEM_FREQUENCY PARAM_VALUE.SYSTEM_FREQUENCY } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.SYSTEM_FREQUENCY}] ${MODELPARAM_VALUE.SYSTEM_FREQUENCY}
}

proc update_MODELPARAM_VALUE.SAMPLING_RATE { MODELPARAM_VALUE.SAMPLING_RATE PARAM_VALUE.SAMPLING_RATE } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.SAMPLING_RATE}] ${MODELPARAM_VALUE.SAMPLING_RATE}
}

