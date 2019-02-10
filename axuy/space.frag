#version 330

uniform vec3 bg;
uniform vec3 color;

in float depth;
out vec4 f_color;

void main() {
	if (depth < 1) {
		f_color = vec4(bg * depth + color * (1 - depth), 1.0);
	} else {
		f_color = vec4(bg, 1.0);
	}
}
