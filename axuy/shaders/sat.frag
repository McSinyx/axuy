#version 330

uniform sampler2D tex;

in vec2 in_text;
out vec4 f_color;

void main(void)
{
	f_color = texture(tex, in_text) * 0.5;
	float r = f_color.r, g = f_color.g, b = f_color.b;
	f_color *= abs(r - g) + abs(g - b) + abs(b - r);
}
