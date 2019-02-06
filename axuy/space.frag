#version 330

uniform vec3 color;
in float alpha;
out vec4 f_color;

void main() {
	f_color = vec4(color, alpha);
}
