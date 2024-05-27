OPENQASM 2.0;
include "qelib1.inc";
gate rzx(param0) q0,q1 { h q1; cx q0,q1; rz(param0) q1; cx q0,q1; h q1; }
gate ecr q0,q1 { rzx(pi/4) q0,q1; x q0; rzx(-pi/4) q0,q1; }
qreg q[127];
creg c[2];
rz(-pi/2) q[14];
sx q[14];
rz(1.77637865138112) q[14];
rz(-1.7126933813990606) q[18];
sx q[18];
rz(-pi/2) q[18];
ecr q[14],q[18];
rz(-2.936010329003569) q[14];
sx q[14];
rz(pi/2) q[14];
rz(pi/2) q[18];
sx q[18];
rz(-0.14189705460416402) q[18];
measure q[14] -> c[0];
measure q[18] -> c[1];