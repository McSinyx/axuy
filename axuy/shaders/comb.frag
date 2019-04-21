#version 330

uniform sampler2D la;
uniform sampler2D tex;

in vec2 in_text;
out vec4 f_color;

void main(void)
{
	f_color = texture(la, in_text) * 0.42 + texture(tex, in_text);
}
