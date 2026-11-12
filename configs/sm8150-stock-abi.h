/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * The released SM8150 sources renamed identifiers still used by the final
 * stock kernels. Apply these aliases to the actual C compilation as well as
 * genksyms; do not override CRCs or hide different layouts from the checker.
 */
#ifndef ONEPLUS7_STOCK_ABI_H
#define ONEPLUS7_STOCK_ABI_H

#define oplus_jank_monitor_info oppo_jank_monitor_info
#define oplus_jank_info oppo_jank_info

#define oplus_display_power_status oppo_display_power_status
#define OPLUS_DISPLAY_POWER_OFF OPPO_DISPLAY_POWER_OFF
#define OPLUS_DISPLAY_POWER_DOZE OPPO_DISPLAY_POWER_DOZE
#define OPLUS_DISPLAY_POWER_ON OPPO_DISPLAY_POWER_ON
#define OPLUS_DISPLAY_POWER_DOZE_SUSPEND OPPO_DISPLAY_POWER_DOZE_SUSPEND
#define OPLUS_DISPLAY_POWER_ON_UNKNOW OPPO_DISPLAY_POWER_ON_UNKNOW
#define oplus_display_scene oppo_display_scene
#define OPLUS_DISPLAY_NORMAL_SCENE OPPO_DISPLAY_NORMAL_SCENE
#define OPLUS_DISPLAY_NORMAL_HBM_SCENE OPPO_DISPLAY_NORMAL_HBM_SCENE
#define OPLUS_DISPLAY_AOD_SCENE OPPO_DISPLAY_AOD_SCENE
#define OPLUS_DISPLAY_AOD_HBM_SCENE OPPO_DISPLAY_AOD_HBM_SCENE
#define OPLUS_DISPLAY_UNKNOW_SCENE OPPO_DISPLAY_UNKNOW_SCENE

#define oplus_motor_chip oppo_motor_chip
#define oplus_motor_operations oppo_motor_operations
#define oplus_dhall_chip oppo_dhall_chip
#define oplus_dhall_operations oppo_dhall_operations

#define get_Oplus_Boot_Mode get_Oppo_Boot_Mode
#define get_oplus_display_power_status get_oppo_display_power_status
#define get_oplus_display_scene get_oppo_display_scene
#define get_oplus_feature get_oppo_feature
#define oplus_daily_build oppo_daily_build
#define oplus_display_get_resolution oppo_display_get_resolution
#define oplus_display_register_client oppo_display_register_client
#define oplus_display_unregister_client oppo_display_unregister_client
#define oplus_m1120_reconfig oppo_m1120_reconfig
#define oplus_parse_motor_info oppo_parse_motor_info
#define oplus_switch_fulldump oppo_switch_fulldump

#endif
