OPENQASM 2.0;
include "qelib1.inc";
gate rzx(param0) q0,q1 { h q1; cx q0,q1; rz(param0) q1; cx q0,q1; h q1; }
gate ecr q0,q1 { rzx(pi/4) q0,q1; x q0; rzx(-pi/4) q0,q1; }
qreg q[127];
creg c[3];
rz(pi/2) q[105];
sx q[105];
rz(-1.4350671353987803) q[105];
rz(pi/2) q[106];
sx q[106];
rz(pi/2) q[106];
ecr q[105],q[106];
rz(-3.0058634621936795) q[105];
sx q[105];
rz(-pi/2) q[105];
rz(-pi) q[106];
rz(pi/2) q[107];
sx q[107];
ecr q[107],q[106];
rz(pi/2) q[106];
sx q[106];
rz(pi/2) q[106];
rz(pi/2) q[107];
sx q[107];
rz(-pi/2) q[107];
measure q[105] -> c[0];
measure q[107] -> c[1];
measure q[106] -> c[2];