#version 330

uniform float visibility;
uniform mat4 mvp;

in vec3 in_vert;
out vec3 color;

void main()
{
	gl_Position = mvp * vec4(in_vert, 1.0);
	float Y = 1 / (1 + pow(1 - gl_Position.z, 2) / visibility);
	color = vec3(Y, Y, Y);
}
