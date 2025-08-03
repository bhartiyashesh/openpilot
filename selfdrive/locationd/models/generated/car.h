#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void car_update_25(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_24(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_30(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_26(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_27(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_29(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_28(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_31(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_err_fun(double *nom_x, double *delta_x, double *out_7629224517445683623);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_210116588889411119);
void car_H_mod_fun(double *state, double *out_6378992956165113570);
void car_f_fun(double *state, double dt, double *out_5950310489973727462);
void car_F_fun(double *state, double dt, double *out_7830899161486897927);
void car_h_25(double *state, double *unused, double *out_5244919079419319843);
void car_H_25(double *state, double *unused, double *out_8526151893442493982);
void car_h_24(double *state, double *unused, double *out_4512082700621470712);
void car_H_24(double *state, double *unused, double *out_5100270675611069371);
void car_h_30(double *state, double *unused, double *out_1607469551165297493);
void car_H_30(double *state, double *unused, double *out_8655490840585734052);
void car_h_26(double *state, double *unused, double *out_996935769643400158);
void car_H_26(double *state, double *unused, double *out_7869297829332182078);
void car_h_27(double *state, double *unused, double *out_8281705130863652528);
void car_H_27(double *state, double *unused, double *out_7616489921323392653);
void car_h_29(double *state, double *unused, double *out_3394203716495548152);
void car_H_29(double *state, double *unused, double *out_8145259496271341868);
void car_h_28(double *state, double *unused, double *out_4823171706959868525);
void car_H_28(double *state, double *unused, double *out_5219085560368679174);
void car_h_31(double *state, double *unused, double *out_5520113141703825732);
void car_H_31(double *state, double *unused, double *out_8495505931565533554);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}