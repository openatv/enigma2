#ifndef _HUFFMAN_H_
#define _HUFFMAN_H_

typedef struct struct_huffman_node
{
	char				*value;
	struct struct_huffman_node	*p0;
	struct struct_huffman_node	*p1;
} type_huffman_node;

bool huffman_read_dictionary (char *file);
void huffman_free_dictionary ();
void huffman_free_node (type_huffman_node *node);
bool huffman_decode (const unsigned char *data, int length, char *result, int result_max_length, bool huffman_debug);

#endif // _HUFFMAN_H_
