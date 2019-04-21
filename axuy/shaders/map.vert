#version 330

uniform mat4 mvp;
uniform vec3 camera;
uniform float visibility;

in vec3 in_vert;
out float intensity;

void main()
{
	gl_Position = mvp * vec4(in_vert, 1.0);
	intensity = 1 / (1 + pow(distance(camera, in_vert), 2) / visibility);
}
