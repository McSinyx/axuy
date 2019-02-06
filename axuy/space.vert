#version 330

uniform mat4 mvp;
uniform vec3 eye;
in vec3 in_vert;
out float alpha;

void main() {
	gl_Position = mvp * vec4(in_vert, 1.0);
	alpha = 1 - distance(eye, in_vert) / 4;
}
