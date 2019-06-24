#version 330

uniform vec3 pos;
uniform mat4 rot;

in vec4 in_vert;

void main()
{
	gl_Position = rot * in_vert + vec4(pos, 0.0);
}
