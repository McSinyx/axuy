#version 330

uniform vec3 color;

in float depth;
out vec4 f_color;

void main() {
	f_color = vec4(color, 1 - depth);
}
