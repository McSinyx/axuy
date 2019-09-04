#version 330

const float SAT = 0.123456789;
const vec3 SIZE = vec3(12, 12, 9);
const vec3 K = acos(-1) / 1.5 / SIZE;
const mat3 YUV = mat3(1.0, 1.0, 1.0,
                      0.0, -0.39465, 2.03211,
                      1.13983, -0.58060, 0.0);

uniform float visibility;
uniform mat4 mvp;

in vec3 in_vert;
out vec3 color;

void main()
{
	gl_Position = mvp * vec4(in_vert, 1.0);
	float Y = 1 / (1 + pow(1 - gl_Position.z, 2) / visibility);
	vec3 vert = mod((in_vert + SIZE), SIZE) * K;
	float angle = vert.x + vert.y + vert.z;
	color = YUV * vec3(Y, cos(angle) * SAT, sin(angle) * SAT);
}
