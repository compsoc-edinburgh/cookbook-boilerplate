server: generate_thumbnails.py parse_content.py content_raw fonts layouts static config.yaml
	python3.9 parse_content.py \
			-i content_raw \
			-o content/recipes
	python3.9 generate_thumbnails.py \
			-i content/recipes \
			-o content/recipes \
			-serif fonts/PlayfairDisplay-Regular.ttf \
			-sansserif fonts/Lato-Regular.ttf
	hugo server

clean:
	rm -rf public resources
	cd content/recipes && ls | grep -v view-all.md | xargs rm -r
