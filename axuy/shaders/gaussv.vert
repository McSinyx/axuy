#version 330

uniform float height;

in vec2 in_vert;
out vec2 coords[13];

void main(void)
{
	gl_Position = vec4(in_vert, 0.0, 1.0);
	vec2 center = in_vert * 0.5 + 0.5;
	float size = 1.0 / height;

	for (int i = 0; i < 13; ++i)
		coords[i] = center + vec2(0.0, (i - 6.0) * size);
}
