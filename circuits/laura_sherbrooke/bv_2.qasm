OPENQASM 2.0;
include "qelib1.inc";
gate rzx(param0) q0,q1 { h q1; cx q0,q1; rz(param0) q1; cx q0,q1; h q1; }
gate ecr q0,q1 { rzx(pi/4) q0,q1; x q0; rzx(-pi/4) q0,q1; }
qreg q[127];
creg c[2];
rz(-pi/2) q[91];
sx q[91];
rz(-0.6822739415210606) q[91];
sx q[91];
rz(pi/2) q[91];
x q[98];
ecr q[98],q[91];
rz(pi/2) q[91];
sx q[91];
rz(-0.888522385273836) q[91];
sx q[91];
rz(-pi/2) q[91];
x q[98];
rz(pi/2) q[98];
measure q[91] -> c[0];
measure q[98] -> c[1];